import pythoncom
import win32gui
import win32con
from win32com.client import Dispatch, gencache


class KompasConnector:
    def __init__(self):
        self.module5 = None
        self.module7 = None
        self.const3d = None
        self.api5 = None
        self.api7 = None
        self.doc3d_api5 = None
        self.doc3d_api7 = None
        self.is_connected = False

    def connect(self) -> dict:
        try:
            pythoncom.CoInitialize()

            self.const3d = gencache.EnsureModule("{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0).constants
            self.module5 = gencache.EnsureModule("{0422828C-F174-495E-AC5D-D31014DBBE87}", 0, 1, 0)
            self.module7 = gencache.EnsureModule("{69AC2981-37C0-4379-84FD-5DD2F3C0A520}", 0, 1, 0)

            raw_api5 = Dispatch("Kompas.Application.5")
            self.api5 = self.module5.KompasObject(
                raw_api5._oleobj_.QueryInterface(self.module5.KompasObject.CLSID, pythoncom.IID_IDispatch)
            )

            raw_api7 = Dispatch("Kompas.Application.7")
            self.api7 = self.module7.IApplication(
                raw_api7._oleobj_.QueryInterface(self.module7.IApplication.CLSID, pythoncom.IID_IDispatch)
            )
            self.api7.Visible = True
            self.is_connected = True
            self.bring_to_front()

            return {"status": "connected", "has_doc": self._check_active_doc()}
        except Exception as e:
            self.is_connected = False
            return {"status": "error", "message": str(e)}

    def bring_to_front(self):
        try:
            hwnd = self.api5.ksGetHWindow()
            if hwnd:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _check_active_doc(self) -> bool:
        if not self.api7:
            return False
        active_doc = self.api7.ActiveDocument
        if active_doc and active_doc.DocumentType == 4:
            self.doc3d_api7 = active_doc
            self.doc3d_api5 = self.api5.ActiveDocument3D()
            return True
        return False

    def ensure_part_document(self) -> bool:
        if self._check_active_doc():
            return True
        try:
            self.doc3d_api7 = self.api7.Documents.Add(4, True)
            self.doc3d_api5 = self.api5.ActiveDocument3D()
            return True
        except Exception:
            return False