import os
import sys
import time
import shutil
import subprocess
import pythoncom
import win32com.client
from win32com.client import gencache
import win32gui
import win32con

class KompasConnector:
    def __init__(self):
        self.api5 = None
        self.api7 = None
        self.module5 = None
        self.module7 = None
        self.const = None
        self.doc3d_api5 = None
        self.part_api5 = None
        self.doc_api7 = None
        self.is_connected = False

    def _clear_gen_py(self):
        gen_path = getattr(win32com, "__gen_path__", None)
        if gen_path and os.path.exists(gen_path):
            shutil.rmtree(gen_path, ignore_errors=True)
            os.makedirs(gen_path, exist_ok=True)
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("win32com.gen_py"):
                sys.modules.pop(mod_name, None)

    def _load_typelibs(self):
        try:
            gencache.is_readonly = False
            self.module5 = gencache.EnsureModule('{0422828C-F174-495E-AC5D-D31014DBBE87}', 0, 1, 0)
            self.module7 = gencache.EnsureModule('{69AC2981-37C0-4379-84FD-5DD2F3C0A520}', 0, 1, 0)
            self.const = gencache.EnsureModule('{2CAF168C-7961-4B90-9DA2-701419BEEFE3}', 0, 1, 0).constants
            if not hasattr(self.module5, "KompasObject") or not hasattr(self.module7, "IApplication"):
                raise AttributeError("Поврежден кэш gen_py")
        except Exception:
            self._clear_gen_py()
            self.module5 = gencache.EnsureModule('{0422828C-F174-495E-AC5D-D31014DBBE87}', 0, 1, 0)
            self.module7 = gencache.EnsureModule('{69AC2981-37C0-4379-84FD-5DD2F3C0A520}', 0, 1, 0)
            self.const = gencache.EnsureModule('{2CAF168C-7961-4B90-9DA2-701419BEEFE3}', 0, 1, 0).constants

    def _launch_kompas_process_if_needed(self):
        kompas_exe = r"D:\Programs\KOMPAS-3D\Bin\KOMPAS.Exe"
        if os.path.exists(kompas_exe):
            try:
                subprocess.Popen([kompas_exe])
                return True
            except Exception:
                return False
        return False

    def _refresh_active_doc_pointers(self):
        if not self.api5 or not self.api7:
            self.doc3d_api5 = None
            self.part_api5 = None
            self.doc_api7 = None
            return False
        try:
            doc7 = self.api7.ActiveDocument
            if doc7 is not None and doc7.DocumentType == 4:
                self.doc_api7 = doc7
                raw_doc5 = self.api5.ActiveDocument3D()
                if raw_doc5 is not None:
                    self.doc3d_api5 = self.module5.ksDocument3D(
                        raw_doc5._oleobj_.QueryInterface(self.module5.ksDocument3D.CLSID, pythoncom.IID_IDispatch)
                    )
                    raw_part = self.doc3d_api5.GetPart(self.const.pTop_Part)
                    if raw_part is not None:
                        self.part_api5 = self.module5.ksPart(
                            raw_part._oleobj_.QueryInterface(self.module5.ksPart.CLSID, pythoncom.IID_IDispatch)
                        )
                        return True
            self.doc3d_api5 = None
            self.part_api5 = None
            self.doc_api7 = None
            return False
        except Exception:
            self.doc3d_api5 = None
            self.part_api5 = None
            self.doc_api7 = None
            return False

    def connect(self):
        pythoncom.CoInitialize()
        try:
            self._load_typelibs()
            raw_api5 = None
            try:
                raw_api5 = win32com.client.GetActiveObject("Kompas.Application.5")
            except Exception:
                try:
                    raw_api5 = win32com.client.Dispatch("Kompas.Application.5")
                except Exception:
                    if self._launch_kompas_process_if_needed():
                        for _ in range(30):
                            time.sleep(0.5)
                            try:
                                raw_api5 = win32com.client.GetActiveObject("Kompas.Application.5")
                                if raw_api5 is not None:
                                    break
                            except Exception:
                                pass
            if raw_api5 is None:
                self.is_connected = False
                return False, "Не удалось запустить или найти КОМПАС-3D."
            last_err = None
            for _ in range(25):
                try:
                    ole5 = getattr(raw_api5, "_oleobj_", None)
                    if ole5 is None and hasattr(raw_api5, "_dispobj_"):
                        ole5 = raw_api5._dispobj_._oleobj_
                    self.api5 = self.module5.KompasObject(
                        ole5.QueryInterface(self.module5.KompasObject.CLSID, pythoncom.IID_IDispatch)
                    )
                    self.api5.Visible = True
                    try:
                        raw_api7 = win32com.client.GetActiveObject("Kompas.Application.7")
                    except Exception:
                        raw_api7 = win32com.client.Dispatch("Kompas.Application.7")
                    ole7 = getattr(raw_api7, "_oleobj_", None)
                    if ole7 is None and hasattr(raw_api7, "_dispobj_"):
                        ole7 = raw_api7._dispobj_._oleobj_
                    self.api7 = self.module7.IApplication(
                        ole7.QueryInterface(self.module7.IApplication.CLSID, pythoncom.IID_IDispatch)
                    )
                    self.api7.Visible = True
                    self.is_connected = True
                    self._refresh_active_doc_pointers()
                    self.bring_to_front()
                    return True, "Подключено к КОМПАС-3D"
                except Exception as e:
                    last_err = e
                    time.sleep(0.5)
            self.is_connected = False
            return False, f"Ошибка инициализации API КОМПАС-3D: {str(last_err)}"
        except Exception as e:
            self.is_connected = False
            return False, f"Ошибка подключения к КОМПАС-3D: {str(e)}"

    def disconnect(self):
        self.api5 = None
        self.api7 = None
        self.doc3d_api5 = None
        self.part_api5 = None
        self.doc_api7 = None
        self.is_connected = False
        return True, "Отключено от КОМПАС-3D"

    def _get_kompas_hwnd(self):
        hwnds = []
        try:
            def enum_handler(hwnd, result_list):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "КОМПАС-3D" in title or "KOMPAS-3D" in title:
                        result_list.append(hwnd)
            win32gui.EnumWindows(enum_handler, hwnds)
        except Exception:
            pass
        return hwnds[0] if hwnds else 0

    def bring_to_front(self):
        try:
            target = self._get_kompas_hwnd()
            if target:
                if win32gui.IsIconic(target):
                    win32gui.ShowWindow(target, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target)
        except Exception:
            pass

    def ensure_document(self):
        if not self.is_connected or not self.api7 or not self.api5:
            ok, msg = self.connect()
            if not ok:
                return None, None, msg
        for _ in range(15):
            try:
                doc7 = self.api7.ActiveDocument
                if doc7 is None or doc7.DocumentType != 4:
                    docs = self.api7.Documents
                    doc7 = docs.Add(4, True)
                if self._refresh_active_doc_pointers():
                    self.bring_to_front()
                    return self.doc3d_api5, self.part_api5, "Документ 3D готов"
                time.sleep(0.4)
            except Exception:
                time.sleep(0.4)
        ok, msg = self.connect()
        if not ok:
            return None, None, msg
        return None, None, "Не удалось создать 3D-документ в КОМПАС-3D."

    def create_new_project(self, project_name=""):
        if not self.is_connected or not self.api7:
            ok, msg = self.connect()
            if not ok:
                return False, msg
        try:
            docs = self.api7.Documents
            docs.Add(4, True)
            time.sleep(0.3)
            self._refresh_active_doc_pointers()
            if project_name and self.part_api5:
                clean_name = project_name.replace(".m3d", "").strip()
                self.part_api5.name = clean_name
                self.part_api5.Update()
            self.bring_to_front()
            label = f" \"{project_name}\"" if project_name else ""
            return True, f"Создан новый 3D-проект{label} (.m3d)"
        except Exception as e:
            return False, f"Ошибка создания нового проекта: {str(e)}"

    def save_project_dialog(self, suggested_name=""):
        doc5, part5, msg = self.ensure_document()
        if not doc5 or not self.doc_api7:
            return False, msg
        default_name = suggested_name.strip() if suggested_name else ""
        if not default_name:
            doc_title = getattr(self.doc_api7, "Name", "") or "Деталь"
            default_name = doc_title
        if not default_name.lower().endswith(".m3d"):
            default_name += ".m3d"
        if part5 and suggested_name:
            part5.name = suggested_name.replace(".m3d", "").strip()
            part5.Update()
        self.bring_to_front()
        hwnd = self._get_kompas_hwnd()
        initial_dir = os.path.expanduser("~\\Documents")
        try:
            flags = win32con.OFN_EXPLORER | win32con.OFN_OVERWRITEPROMPT | win32con.OFN_PATHMUSTEXIST
            file_path, _, _ = win32gui.GetSaveFileNameW(
                hwndOwner=hwnd,
                Filter="Детали КОМПАС-3D (*.m3d)\0*.m3d\0Все файлы (*.*)\0*.*\0",
                FilterIndex=1,
                File=default_name,
                InitialDir=initial_dir,
                Title="Сохранение 3D-проекта КОМПАС-3D",
                Flags=flags,
                DefExt="m3d"
            )
            if not file_path:
                return False, "Сохранение отменено пользователем"
            saved = False
            try:
                saved = bool(self.doc_api7.SaveAs(file_path))
            except Exception:
                saved = False
            if not saved and self.doc3d_api5:
                saved = bool(self.doc3d_api5.SaveAs(file_path))
            return True, f"Проект успешно сохранен: {file_path}"
        except Exception as e:
            return False, f"Сохранение отменено или возникла ошибка: {str(e)}"

    def delete_project(self, target_name=""):
        if not self.is_connected or not self.api7:
            return False, "Нет активного подключения к КОМПАС-3D"
        try:
            doc7 = self.api7.ActiveDocument
            if doc7 is None:
                return False, "В КОМПАС-3D нет открытого проекта для удаления"
            doc_name = getattr(doc7, "Name", "")
            doc_path = getattr(doc7, "PathName", "")
            doc7.Close(False)
            self._refresh_active_doc_pointers()
            removed_from_disk = False
            if doc_path and os.path.exists(doc_path) and doc_path.lower().endswith(".m3d"):
                try:
                    os.remove(doc_path)
                    removed_from_disk = True
                except Exception:
                    pass
            elif target_name:
                cand = target_name if target_name.lower().endswith(".m3d") else target_name + ".m3d"
                doc_dir = os.path.join(os.path.expanduser("~\\Documents"), cand)
                if os.path.exists(doc_dir):
                    try:
                        os.remove(doc_dir)
                        removed_from_disk = True
                    except Exception:
                        pass
            if removed_from_disk:
                return True, f"Проект \"{doc_name or target_name}\" закрыт и удален с диска"
            return True, f"Проект \"{doc_name or 'Деталь'}\" закрыт без сохранения"
        except Exception as e:
            return False, f"Ошибка удаления проекта: {str(e)}"

    def get_status(self):
        pythoncom.CoInitialize()
        if not self.is_connected or not self.api7:
            return {"connected": False, "doc_open": False, "doc_name": ""}
        try:
            doc = self.api7.ActiveDocument
            if doc is not None and doc.DocumentType == 4:
                self._refresh_active_doc_pointers()
                return {"connected": True, "doc_open": True, "doc_name": doc.Name}
            self.doc3d_api5 = None
            self.part_api5 = None
            self.doc_api7 = None
            return {"connected": True, "doc_open": False, "doc_name": ""}
        except Exception:
            self.is_connected = False
            self.api5 = None
            self.api7 = None
            self.doc3d_api5 = None
            self.part_api5 = None
            self.doc_api7 = None
            return {"connected": False, "doc_open": False, "doc_name": ""}