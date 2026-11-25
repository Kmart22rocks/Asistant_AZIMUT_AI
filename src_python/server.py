import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import pythoncom
from kompas_connector import KompasConnector
from tree_scanner import TreeScanner
from features.plate_feature import PlateFeature
from features.holes_feature import CornerHolesFeature
from features.cylinder_feature import CylinderFeature, TubeFeature, PolygonPrismFeature, ConeFeature
from features.cut_feature import SingleHoleFeature, CircularHolesFeature, CutBoxFeature
from features.edge_feature import ChamferFeature, FilletFeature
from features.custom_feature import CustomProfileFeature, SlotFeature, SphereFeature
from features.advanced_feature import ShellFeature, HolesGridFeature, SteppedShaftFeature, AppearanceFeature
from features.profile_shapes_feature import RectTubeFeature, LProfileFeature, UProfileFeature, IBeamFeature, TBeamFeature
from features.kinematic_feature import TorusFeature, DomeFeature, SpringFeature, GearFeature, FlangeFeature, RibFeature
from features.machining_feature import CounterboreFeature, CountersinkFeature, GrooveFeature, CrossSlotFeature, TSlotFeature
from features.standard_part_feature import StandardPartFeature
def free_port_8765():
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
        current_pid = os.getpid()
        for line in out.splitlines():
            if "127.0.0.1:8765" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid != current_pid and pid > 0:
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
class AzimutCadEngine:
    BOSS_TYPES = (
        "plate", "box", "cube", "cylinder", "tube", "polygon", "cone", "profile", "shaft", "sphere",
        "rect_tube", "l_profile", "u_profile", "i_beam", "t_beam",
        "torus", "dome", "spring", "gear", "flange", "rib",
        "standard_part", "bolt", "nut", "washer", "screw", "bearing", "pin", "key"
    )
    CUT_TYPES = (
        "hole", "holes_circ", "holes_grid", "cut_box", "slot",
        "counterbore", "countersink", "groove", "cross_slot", "t_slot"
    )
    def __init__(self):
        self.connector = KompasConnector()
        self.features = {}
        self.feature_order = []
        self.active_doc_name = ""
        self.active_part_ptr = None
    def _create_feature_instance(self, f_type, f_id):
        mapping = {
            "plate": PlateFeature,
            "box": PlateFeature,
            "cube": PlateFeature,
            "holes_corner": CornerHolesFeature,
            "cylinder": CylinderFeature,
            "tube": TubeFeature,
            "polygon": PolygonPrismFeature,
            "cone": ConeFeature,
            "hole": SingleHoleFeature,
            "holes_circ": CircularHolesFeature,
            "holes_grid": HolesGridFeature,
            "cut_box": CutBoxFeature,
            "chamfer": ChamferFeature,
            "fillet": FilletFeature,
            "profile": CustomProfileFeature,
            "slot": SlotFeature,
            "sphere": SphereFeature,
            "shell": ShellFeature,
            "shaft": SteppedShaftFeature,
            "appearance": AppearanceFeature,
            "rect_tube": RectTubeFeature,
            "l_profile": LProfileFeature,
            "u_profile": UProfileFeature,
            "i_beam": IBeamFeature,
            "t_beam": TBeamFeature,
            "torus": TorusFeature,
            "dome": DomeFeature,
            "spring": SpringFeature,
            "gear": GearFeature,
            "flange": FlangeFeature,
            "rib": RibFeature,
            "counterbore": CounterboreFeature,
            "countersink": CountersinkFeature,
            "groove": GrooveFeature,
            "cross_slot": CrossSlotFeature,
            "t_slot": TSlotFeature,
            "standard_part": StandardPartFeature,
            "bolt": StandardPartFeature,
            "nut": StandardPartFeature,
            "washer": StandardPartFeature,
            "screw": StandardPartFeature,
            "bearing": StandardPartFeature,
            "pin": StandardPartFeature,
            "key": StandardPartFeature
        }
        cls = mapping.get(f_type)
        if cls:
            feat = cls(f_id, self.connector)
            feat.feature_type = f_type
            return feat
        return None
    def _sync_document_state(self, doc5, part5):
        try:
            doc_info = self.connector.get_status()
            doc_name = doc_info.get("doc_name", "")
            part_ptr = int(part5._oleobj_) if hasattr(part5, "_oleobj_") else id(part5)
            if (self.active_doc_name and self.active_doc_name != doc_name) or (self.active_part_ptr and self.active_part_ptr != part_ptr):
                self.features.clear()
                self.feature_order.clear()
            self.active_doc_name = doc_name
            self.active_part_ptr = part_ptr
        except Exception:
            pass
        stale_ids = []
        for fid, feat in self.features.items():
            if not feat.is_alive():
                stale_ids.append(fid)
        for fid in stale_ids:
            self.features.pop(fid, None)
            if fid in self.feature_order:
                self.feature_order.remove(fid)
    def _get_feature_bounds(self, feat):
        p = feat.params
        cx = float(p.get("x", 0.0))
        cz = float(p.get("z", 0.0))
        y0 = float(p.get("y_offset", p.get("z_offset", 0.0)))
        if feat.feature_type == "sphere":
            r = abs(float(p.get("diameter", p.get("d", 40.0)))) / 2.0
            return {"center_x": cx, "center_z": cz, "bottom_y": y0 - r, "top_y": y0 + r, "center_y": y0}
        h = abs(float(p.get("thickness", p.get("height", p.get("h", p.get("size", p.get("side", 0.0)))))))
        dir_sign = -1 if float(p.get("direction", 1)) < 0 else 1
        if dir_sign > 0:
            bottom_y = y0
            top_y = y0 + h
        else:
            top_y = y0
            bottom_y = y0 - h
        return {"center_x": cx, "center_z": cz, "bottom_y": bottom_y, "top_y": top_y, "center_y": (bottom_y + top_y) / 2.0}
    def _get_reference_boss(self, target_id=""):
        if target_id and target_id in self.features:
            return self.features[target_id]
        for fid in reversed(self.feature_order):
            feat = self.features.get(fid)
            if feat and feat.feature_type in self.BOSS_TYPES:
                return feat
        return None
    def _fill_base_plate_dims(self, params):
        if "plate_width" in params and "plate_length" in params:
            return
        for fid in self.feature_order:
            feat = self.features.get(fid)
            if feat and feat.feature_type in ("plate", "box", "cube"):
                params.setdefault("plate_width", feat.params.get("width", 100.0))
                params.setdefault("plate_length", feat.params.get("length", 100.0))
                return
    def execute_commands(self, payload):
        print(f"Выполнение команд ИИ: {json.dumps(payload, ensure_ascii=False)}", flush=True)
        commands = payload.get("commands", [])
        logs = []
        for cmd in commands:
            action = cmd.get("action", "build")
            f_id = cmd.get("id", "")
            f_type = cmd.get("type", "")
            params = dict(cmd.get("params", {}))
            if "y" in params and "y_offset" not in params:
                params["y_offset"] = params.pop("y")
            if action == "doc_new" or f_type == "doc_new":
                proj_name = params.get("name", params.get("filename", ""))
                ok, res_msg = self.connector.create_new_project(proj_name)
                if ok:
                    self.features.clear()
                    self.feature_order.clear()
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs
                continue
            if action == "doc_save" or f_type == "doc_save":
                proj_name = params.get("name", params.get("filename", ""))
                ok, res_msg = self.connector.save_project_dialog(proj_name)
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs
                continue
            if action == "doc_delete" or f_type == "doc_delete":
                proj_name = params.get("name", params.get("filename", ""))
                ok, res_msg = self.connector.delete_project(proj_name)
                if ok:
                    self.features.clear()
                    self.feature_order.clear()
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs
                continue
            doc5, part5, msg = self.connector.ensure_document()
            if not doc5 or not part5:
                return False, msg, logs
            self._sync_document_state(doc5, part5)
            sel = TreeScanner.get_selected_info(self.connector)
            has_selected_face = sel.get("selected_faces", 0) > 0
            has_selected_edge = sel.get("selected_edges", 0) > 0
            if f_type in ("chamfer", "fillet") and (has_selected_edge or has_selected_face):
                action = "build"
                f_id = f"{f_type}_{len(self.feature_order) + 1}"
            if action == "clear":
                for fid in reversed(list(self.feature_order)):
                    feat = self.features.get(fid)
                    if feat:
                        feat.sync_refs(doc5, part5)
                        feat.delete()
                self.features.clear()
                self.feature_order.clear()
                logs.append("Деталь полностью очищена")
                continue
            if action == "undo":
                if self.feature_order:
                    last_id = self.feature_order.pop()
                    feat = self.features.pop(last_id, None)
                    if feat:
                        feat.sync_refs(doc5, part5)
                        feat.delete()
                        logs.append(f"Отменена операция: {last_id}")
                else:
                    logs.append("Нет операций для отмены")
                continue
            if action == "delete":
                target_id = f_id
                if not target_id and f_type:
                    for fid in reversed(self.feature_order):
                        if self.features[fid].feature_type == f_type:
                            target_id = fid
                            break
                if target_id and target_id in self.features:
                    feat = self.features.pop(target_id)
                    if target_id in self.feature_order:
                        self.feature_order.remove(target_id)
                    feat.sync_refs(doc5, part5)
                    feat.delete()
                    logs.append(f"Удален элемент: {target_id}")
                else:
                    logs.append(f"Элемент для удаления не найден: {target_id or f_type}")
                continue
            if action == "update":
                target_feat = self.features.get(f_id)
                if target_feat and f_type and target_feat.feature_type != f_type:
                    rect_group = ("plate", "box", "cube")
                    if not (target_feat.feature_type in rect_group and f_type in rect_group):
                        target_feat = None
                if not target_feat and f_type:
                    rect_group = ("plate", "box", "cube")
                    for fid in reversed(self.feature_order):
                        existing_t = self.features[fid].feature_type
                        if existing_t == f_type or (existing_t in rect_group and f_type in rect_group):
                            target_feat = self.features[fid]
                            f_id = fid
                            break
                if target_feat:
                    target_feat.sync_refs(doc5, part5)
                    if f_type in ("plate", "box", "cube"):
                        target_feat.feature_type = f_type
                    if target_feat.feature_type == "holes_corner":
                        self._fill_base_plate_dims(params)
                    ok, res_msg = target_feat.update(params)
                    logs.append(res_msg)
                    if not ok:
                        return False, res_msg, logs
                    continue
                else:
                    action = "build"
                    f_id = f"{f_type}_{len(self.feature_order) + 1}"
            if not f_id:
                f_id = f"{f_type}_{len(self.feature_order) + 1}"
            if action == "build":
                if f_id in self.features and self.features[f_id].feature_type == f_type and f_type not in ("chamfer", "fillet"):
                    target_feat = self.features[f_id]
                    target_feat.sync_refs(doc5, part5)
                    ok, res_msg = target_feat.update(params)
                    logs.append(res_msg)
                    if not ok:
                        return False, res_msg, logs
                else:
                    if f_id in self.features:
                        f_id = f"{f_type}_{len(self.feature_order) + 1}"
                    ref_boss = self._get_reference_boss(str(params.get("align_to", params.get("base_id", ""))))
                    if f_type in self.BOSS_TYPES and ref_boss is None and not has_selected_face:
                        params["x"] = 0.0
                        params["z"] = 0.0
                        params["y_offset"] = 0.0
                        params["z_offset"] = 0.0
                        params.setdefault("direction", 1)
                    elif ref_boss is not None and not has_selected_face and f_type in (self.BOSS_TYPES + self.CUT_TYPES):
                        b = self._get_feature_bounds(ref_boss)
                        if "x" not in params:
                            params["x"] = b["center_x"]
                        if "z" not in params:
                            params["z"] = b["center_z"]
                        base_mode = str(params.get("base", "")).strip().lower()
                        dir_val = float(params.get("direction", 1))
                        if base_mode in ("bottom", "низ", "нижнее", "снизу"):
                            params["y_offset"] = b["bottom_y"]
                            params["z_offset"] = b["bottom_y"]
                            if f_type in self.BOSS_TYPES and "direction" not in params:
                                params["direction"] = -1
                        elif base_mode in ("top", "верх", "верхнее", "сверху"):
                            params["y_offset"] = b["top_y"]
                            params["z_offset"] = b["top_y"]
                            if f_type in self.BOSS_TYPES and "direction" not in params:
                                params["direction"] = 1
                        elif base_mode in ("center", "центр"):
                            params["y_offset"] = b["center_y"]
                            params["z_offset"] = b["center_y"]
                        elif "y_offset" not in params and "z_offset" not in params:
                            target_y = b["bottom_y"] if dir_val < 0 else b["top_y"]
                            params["y_offset"] = target_y
                            params["z_offset"] = target_y
                    if "y_offset" in params:
                        params["z_offset"] = params["y_offset"]
                    if f_type == "holes_corner":
                        self._fill_base_plate_dims(params)
                    feat = self._create_feature_instance(f_type, f_id)
                    if not feat:
                        return False, f"Неизвестный тип элемента: {f_type}", logs
                    feat.sync_refs(doc5, part5)
                    ok, res_msg = feat.build(params)
                    if ok:
                        self.features[f_id] = feat
                        if f_id not in self.feature_order:
                            self.feature_order.append(f_id)
                        logs.append(res_msg)
                    else:
                        return False, res_msg, logs
        return True, "Выполнено успешно", logs
    def get_full_status(self):
        st = self.connector.get_status()
        if st.get("connected") and st.get("doc_open") and self.connector.doc3d_api5 and self.connector.part_api5:
            self._sync_document_state(self.connector.doc3d_api5, self.connector.part_api5)
        st["features"] = [
            {
                "id": fid,
                "type": self.features[fid].feature_type,
                "params": self.features[fid].params,
                "bounds": self._get_feature_bounds(self.features[fid])
            }
            for fid in self.feature_order if fid in self.features
        ]
        st["selection"] = TreeScanner.get_selected_info(self.connector)
        st["native_tree"] = TreeScanner.scan_model_tree(self.connector)
        return st
engine = AzimutCadEngine()
class AzimutRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def _send_json(self, status_code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == '/status':
                st = engine.get_full_status()
                self._send_json(200, st)
            elif parsed.path == '/connect':
                ok, msg = engine.connector.connect()
                if ok:
                    engine.connector.ensure_document()
                st = engine.connector.get_status()
                st["message"] = msg
                st["features"] = []
                st["selection"] = TreeScanner.get_selected_info(engine.connector)
                st["native_tree"] = TreeScanner.scan_model_tree(engine.connector)
                self._send_json(200 if ok else 500, st)
            elif parsed.path == '/disconnect':
                ok, msg = engine.connector.disconnect()
                self._send_json(200, {"connected": False, "doc_open": False, "doc_name": "", "message": msg})
            else:
                self._send_json(404, {"error": "Маршрут не найден"})
        except Exception as e:
            self._send_json(500, {"connected": False, "doc_open": False, "doc_name": "", "message": str(e)})
    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            payload = json.loads(raw_body)
        except Exception as e:
            self._send_json(400, {"success": False, "message": f"Ошибка JSON: {str(e)}"})
            return
        if parsed.path == '/execute':
            try:
                ok, msg, logs = engine.execute_commands(payload)
                st = engine.get_full_status()
                self._send_json(200 if ok else 500, {
                    "success": ok,
                    "message": msg,
                    "logs": logs,
                    "status": st
                })
            except Exception as e:
                self._send_json(500, {
                    "success": False,
                    "message": f"Ошибка выполнения: {str(e)}",
                    "logs": [],
                    "status": engine.get_full_status()
                })
        else:
            self._send_json(404, {"error": "Маршрут не найден"})
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    pythoncom.CoInitialize()
    free_port_8765()
    server = HTTPServer(('127.0.0.1', 8765), AzimutRequestHandler)
    print("AZIMUT Python Server started: http://127.0.0.1:8765", flush=True)
    server.serve_forever()