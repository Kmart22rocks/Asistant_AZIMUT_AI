import sys
import os
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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


FEATURE_CLASSES = {
    "plate": PlateFeature,
    "cube": PlateFeature,
    "box": PlateFeature,
    "holes_corner": CornerHolesFeature,
    "cylinder": CylinderFeature,
    "boss_cyl": CylinderFeature,
    "tube": TubeFeature,
    "polygon": PolygonPrismFeature,
    "prism": PolygonPrismFeature,
    "cone": ConeFeature,
    "sphere": SphereFeature,
    "ball": SphereFeature,
    "hole": SingleHoleFeature,
    "cut_cyl": SingleHoleFeature,
    "holes_circ": CircularHolesFeature,
    "holes_grid": HolesGridFeature,
    "cut_box": CutBoxFeature,
    "pocket": CutBoxFeature,
    "slot": SlotFeature,
    "chamfer": ChamferFeature,
    "fillet": FilletFeature,
    "shell": ShellFeature,
    "shaft": SteppedShaftFeature,
    "appearance": AppearanceFeature,
    "color": AppearanceFeature,
    "material": AppearanceFeature,
    "profile": CustomProfileFeature,
    "custom": CustomProfileFeature,
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
    "bolt": StandardPartFeature,
    "nut": StandardPartFeature,
    "washer": StandardPartFeature,
    "screw": StandardPartFeature,
    "bearing": StandardPartFeature,
    "pin": StandardPartFeature,
    "key": StandardPartFeature,
    "standard_part": StandardPartFeature
}

BASE_SHAPES = {
    "plate", "cube", "box", "cylinder", "boss_cyl", "tube", "polygon", "prism",
    "cone", "sphere", "ball", "shaft", "profile", "custom",
    "rect_tube", "l_profile", "u_profile", "i_beam", "t_beam",
    "torus", "dome", "spring", "gear", "flange",
    "bolt", "nut", "washer", "screw", "bearing", "pin", "key", "standard_part"
}

SAVE_DIR = r"D:\Database AZIMUT"


class AzimutCadEngine:
    def __init__(self):
        self.connector = KompasConnector()
        self.features = {}
        self.feature_order = []

    def _are_types_compatible(self, t1, t2):
        if t1 == t2:
            return True
        groups = [
            {"plate", "cube", "box"},
            {"cylinder", "boss_cyl"},
            {"polygon", "prism"},
            {"sphere", "ball"},
            {"hole", "cut_cyl"},
            {"cut_box", "pocket"},
            {"appearance", "color", "material"},
            {"profile", "custom"}
        ]
        for g in groups:
            if t1 in g and t2 in g:
                return True
        return False

    def _make_unique_id(self, f_type, requested_id):
        if requested_id and requested_id != "id_1" and requested_id not in self.features:
            return requested_id
        idx = 1
        while f"{f_type}_{idx}" in self.features:
            idx += 1
        return f"{f_type}_{idx}"

    def _compute_feature_bounds(self, feat):
        p = feat.params
        ftype = feat.feature_type
        cx = float(p.get("x", 0.0))
        cz = float(p.get("z", 0.0))
        y_off = float(p.get("y_offset", p.get("z_offset", 0.0)))
        direction = int(p.get("direction", 1))

        h = float(p.get("height", p.get("depth", p.get("length", p.get("h", 0.0)))))
        if ftype in ("sphere", "ball"):
            r = float(p.get("radius", p.get("r", float(p.get("diameter", p.get("d", 40.0))) / 2.0)))
            return {
                "center_x": cx,
                "center_z": cz,
                "bottom_y": y_off - r,
                "top_y": y_off + r,
                "height": r * 2.0
            }

        if direction >= 0:
            bottom_y = y_off
            top_y = y_off + h
        else:
            bottom_y = y_off - h
            top_y = y_off

        return {
            "center_x": cx,
            "center_z": cz,
            "bottom_y": bottom_y,
            "top_y": top_y,
            "height": h
        }

    def _get_model_vertical_extremes(self):
        if not self.feature_order:
            return 0.0, 0.0
        max_top = -1e9
        min_bottom = 1e9
        found = False
        for fid in self.feature_order:
            feat = self.features.get(fid)
            if not feat or feat.feature_type not in BASE_SHAPES:
                continue
            b = self._compute_feature_bounds(feat)
            if b["top_y"] > max_top:
                max_top = b["top_y"]
            if b["bottom_y"] < min_bottom:
                min_bottom = b["bottom_y"]
            found = True
        if not found:
            return 0.0, 0.0
        return max_top, min_bottom

    def _get_primary_base_feature(self):
        for fid in reversed(self.feature_order):
            f = self.features.get(fid)
            if f and f.feature_type in BASE_SHAPES:
                return f
        return None

    def get_full_status(self):
        st = self.connector.get_status()
        active_features = []
        dead_ids = []
        for fid in self.feature_order:
            f = self.features.get(fid)
            if f:
                if f.is_alive():
                    active_features.append({
                        "id": fid,
                        "type": f.feature_type,
                        "params": f.params,
                        "bounds": self._compute_feature_bounds(f)
                    })
                else:
                    dead_ids.append(fid)

        for did in dead_ids:
            self.features.pop(did, None)
            if did in self.feature_order:
                self.feature_order.remove(did)

        st["features"] = active_features
        st["selection"] = TreeScanner.get_selected_info(self.connector)
        st["tree"] = TreeScanner.scan_model_tree(self.connector)
        return st

    def _save_to_azimut_dir(self, params):
        os.makedirs(SAVE_DIR, exist_ok=True)
        st = self.connector.get_status()
        default_name = st.get("doc_name", "") or "Деталь_АЗИМУТ"
        raw_name = str(params.get("name", params.get("filename", params.get("path", default_name)))).strip()
        if not raw_name:
            raw_name = "Деталь_АЗИМУТ"
        base_name = os.path.basename(raw_name.replace("\\", "/"))
        if not base_name.lower().endswith(".m3d"):
            base_name += ".m3d"
        full_path = os.path.join(SAVE_DIR, base_name)

        doc5, part5, msg = self.connector.ensure_document()
        if not doc5:
            return False, msg

        saved = False
        try:
            saved = bool(doc5.SaveAs(full_path))
        except Exception:
            saved = False

        if not saved and getattr(self.connector, "app7", None) is not None:
            try:
                ad = self.connector.app7.ActiveDocument
                if ad is not None:
                    ad.SaveAs(full_path)
                    saved = True
            except Exception:
                pass

        if saved or os.path.exists(full_path):
            return True, f"Файл успешно сохранен в {full_path}"
        return False, f"Не удалось сохранить файл в {full_path}"

    def _update_and_rebuild_chain(self, target_fid, target_feat, f_type, params, doc5, part5):
        old_x = float(target_feat.params.get("x", 0.0))
        old_z = float(target_feat.params.get("z", 0.0))
        old_y = float(target_feat.params.get("y_offset", target_feat.params.get("z_offset", 0.0)))
        old_h = float(target_feat.params.get("height", target_feat.params.get("depth", target_feat.params.get("h", 0.0))))

        new_x = float(params.get("x", old_x))
        new_z = float(params.get("z", old_z))
        new_y = float(params.get("y_offset", params.get("z_offset", old_y)))

        dx = new_x - old_x
        dz = new_z - old_z
        dy = new_y - old_y

        is_moving = (abs(dx) > 1e-6 or abs(dy) > 1e-6 or abs(dz) > 1e-6)

        if not is_moving:
            if f_type == "cube" or target_feat.feature_type == "cube":
                val = params.get("size", params.get("width", params.get("length", params.get("height"))))
                if val is not None:
                    v = float(val)
                    params["width"] = v
                    params["length"] = v
                    params["height"] = v
                    params["size"] = v
            elif target_feat.feature_type in ("plate", "box"):
                if "size" not in params and any(k in params for k in ("width", "length", "height")):
                    target_feat.params.pop("size", None)
        else:
            for dim_key in ("size", "width", "length", "height", "diameter", "d", "radius", "r"):
                params.pop(dim_key, None)

        target_feat.params.update(params)
        if "y_offset" in params:
            target_feat.params["z_offset"] = float(params["y_offset"])
        elif "z_offset" in params:
            target_feat.params["y_offset"] = float(params["z_offset"])

        new_h = float(target_feat.params.get("height", target_feat.params.get("depth", target_feat.params.get("h", old_h))))
        dh = new_h - old_h

        try:
            sm = part5.SelectMng()
            if sm:
                sm.UnselectAll()
        except Exception:
            pass

        for i in reversed(range(len(self.feature_order))):
            fid = self.feature_order[i]
            feat = self.features.get(fid)
            if feat:
                feat.sync_refs(doc5, part5)
                feat.delete()

        try:
            target_idx = self.feature_order.index(target_fid)
        except ValueError:
            target_idx = 0

        last_msg = "Деталь перестроена"
        for i in range(len(self.feature_order)):
            fid = self.feature_order[i]
            feat = self.features.get(fid)
            if not feat:
                continue
            feat.sync_refs(doc5, part5)

            if fid != target_fid:
                if is_moving:
                    feat.params["x"] = float(feat.params.get("x", 0.0)) + dx
                    feat.params["z"] = float(feat.params.get("z", 0.0)) + dz
                    cur_fy = float(feat.params.get("y_offset", feat.params.get("z_offset", 0.0)))
                    feat.params["y_offset"] = cur_fy + dy
                    feat.params["z_offset"] = cur_fy + dy
                    if "edge_coords" in feat.params and isinstance(feat.params["edge_coords"], list):
                        shifted_coords = []
                        for pt in feat.params["edge_coords"]:
                            if isinstance(pt, (list, tuple)) and len(pt) >= 3:
                                shifted_coords.append([
                                    float(pt[0]) + dx,
                                    float(pt[1]) + dy,
                                    float(pt[2]) + dz
                                ])
                        feat.params["edge_coords"] = shifted_coords
                elif i > target_idx:
                    if abs(dh) > 1e-6 and target_feat.feature_type in BASE_SHAPES:
                        cur_fy = float(feat.params.get("y_offset", feat.params.get("z_offset", 0.0)))
                        if cur_fy >= old_y + old_h - 1e-3:
                            feat.params["y_offset"] = cur_fy + dh
                            feat.params["z_offset"] = cur_fy + dh
                        if "edge_coords" in feat.params and isinstance(feat.params["edge_coords"], list):
                            shifted_coords = []
                            for pt in feat.params["edge_coords"]:
                                if isinstance(pt, (list, tuple)) and len(pt) >= 3:
                                    py = float(pt[1])
                                    if py >= old_y + old_h - 1e-3:
                                        py += dh
                                    shifted_coords.append([float(pt[0]), py, float(pt[2])])
                            feat.params["edge_coords"] = shifted_coords
                    if feat.feature_type == "holes_corner" and target_feat.feature_type in ("plate", "cube", "box"):
                        if "width" in target_feat.params:
                            feat.params["plate_width"] = float(target_feat.params["width"])
                            feat.params["width"] = float(target_feat.params["width"])
                        if "length" in target_feat.params:
                            feat.params["plate_length"] = float(target_feat.params["length"])
                            feat.params["length"] = float(target_feat.params["length"])

            ok, msg = feat.build(feat.params)
            if not ok:
                return False, msg
            if fid == target_fid:
                last_msg = msg

        if is_moving:
            return True, f"{last_msg} (перемещена вся деталь в X={new_x}, Y={new_y}, Z={new_z})"
        return True, last_msg

    def execute_commands(self, payload):
        commands = payload.get("commands", [])
        if not commands and "action" in payload:
            commands = [payload]

        logs = []
        for cmd in commands:
            action = cmd.get("action", "build").lower()
            f_id = cmd.get("id", "feature_1")
            f_type = cmd.get("type", "plate").lower()
            params = cmd.get("params", {})

            if action == "doc_new":
                proj_name = params.get("name", "")
                ok, res_msg = self.connector.create_new_project(proj_name)
                if ok:
                    self.features.clear()
                    self.feature_order.clear()
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs
                continue

            if action in ("doc_save", "save") or f_type in ("doc_save", "save"):
                ok, res_msg = self._save_to_azimut_dir(params)
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs
                continue

            if action == "doc_delete":
                proj_name = params.get("name", "")
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
                return False, msg, [msg]

            if action == "clear":
                for fid in reversed(self.feature_order):
                    feat = self.features.get(fid)
                    if feat:
                        feat.sync_refs(doc5, part5)
                        feat.delete()
                self.features.clear()
                self.feature_order.clear()
                logs.append("Все построенные элементы удалены.")
                continue

            elif action == "undo":
                if self.feature_order:
                    last_id = self.feature_order.pop()
                    feat = self.features.pop(last_id, None)
                    if feat:
                        feat.sync_refs(doc5, part5)
                        feat.delete()
                        logs.append(f"Отменена операция: {last_id}")
                else:
                    logs.append("Нет операций для отмены.")
                continue

            elif action == "delete":
                feat = self.features.get(f_id)
                target_id = f_id
                if feat and not self._are_types_compatible(feat.feature_type, f_type):
                    feat = None
                if not feat:
                    for ex_fid in reversed(self.feature_order):
                        ex_f = self.features.get(ex_fid)
                        if ex_f and self._are_types_compatible(ex_f.feature_type, f_type):
                            feat = ex_f
                            target_id = ex_fid
                            break
                if feat:
                    self.features.pop(target_id, None)
                    if target_id in self.feature_order:
                        self.feature_order.remove(target_id)
                    feat.sync_refs(doc5, part5)
                    feat.delete()
                    logs.append(f"Удален элемент {target_id}")
                else:
                    logs.append(f"Элемент {f_id} не найден для удаления.")
                continue

            elif action == "build":
                cls = FEATURE_CLASSES.get(f_type)
                if not cls:
                    return False, f"Неизвестный тип операции: {f_type}", logs

                sel_info = TreeScanner.get_selected_info(self.connector)
                sel_edges = int(sel_info.get("selected_edges", 0))

                if f_type in ("chamfer", "fillet") and sel_edges == 0:
                    existing_edge_fid = None
                    existing_edge_feat = None
                    for ex_fid in reversed(self.feature_order):
                        ex_f = self.features.get(ex_fid)
                        if ex_f and ex_f.feature_type == f_type:
                            existing_edge_fid = ex_fid
                            existing_edge_feat = ex_f
                            break
                    if existing_edge_feat is not None:
                        ok, res_msg = self._update_and_rebuild_chain(
                            existing_edge_fid, existing_edge_feat, f_type, params, doc5, part5
                        )
                        logs.append(res_msg)
                        if not ok:
                            return False, res_msg, logs
                        continue

                f_id = self._make_unique_id(f_type, f_id)

                if f_type == "cube":
                    val = params.get("size", params.get("width", params.get("length", params.get("height", 50.0))))
                    params["width"] = val
                    params["length"] = val
                    params["height"] = val
                    params["size"] = val

                base_feat = self._get_primary_base_feature()
                if base_feat is None and f_type in BASE_SHAPES:
                    params["x"] = 0.0
                    params["z"] = 0.0
                    params["y_offset"] = 0.0
                    params["z_offset"] = 0.0
                elif base_feat is not None:
                    base_bounds = self._compute_feature_bounds(base_feat)
                    if "x" not in params:
                        params["x"] = base_bounds["center_x"]
                    if "z" not in params and "y" not in params:
                        params["z"] = base_bounds["center_z"]

                    max_top, min_bottom = self._get_model_vertical_extremes()
                    base_pos = str(params.get("base", params.get("position", ""))).lower()
                    direction = int(params.get("direction", 1))

                    if "y_offset" not in params and "z_offset" not in params:
                        if base_pos in ("bottom", "низ", "снизу") or (direction < 0 and f_type in BASE_SHAPES):
                            params["y_offset"] = min_bottom
                            params["z_offset"] = min_bottom
                        elif base_pos in ("top", "верх", "сверху"):
                            params["y_offset"] = max_top
                            params["z_offset"] = max_top
                        else:
                            params["y_offset"] = 0.0
                            params["z_offset"] = 0.0

                    if f_type == "holes_corner":
                        if "plate_width" not in params and "width" not in params:
                            params["plate_width"] = float(base_feat.params.get("width", 100.0))
                        if "plate_length" not in params and "length" not in params:
                            params["plate_length"] = float(base_feat.params.get("length", 100.0))

                if "y_offset" in params and "z_offset" not in params:
                    params["z_offset"] = params["y_offset"]

                params["part_type"] = f_type
                feat = cls(f_id, self.connector)
                feat.feature_type = f_type
                ok, res_msg = feat.build(params)
                if ok:
                    self.features[f_id] = feat
                    self.feature_order.append(f_id)
                logs.append(res_msg)
                if not ok:
                    return False, res_msg, logs

            elif action == "update":
                target_feat = self.features.get(f_id)
                target_fid = f_id
                if target_feat and not self._are_types_compatible(target_feat.feature_type, f_type):
                    target_feat = None
                    target_fid = None

                if not target_feat:
                    for ex_fid in reversed(self.feature_order):
                        ex_f = self.features.get(ex_fid)
                        if ex_f and self._are_types_compatible(ex_f.feature_type, f_type):
                            target_feat = ex_f
                            target_fid = ex_fid
                            break

                if target_feat:
                    ok, res_msg = self._update_and_rebuild_chain(target_fid, target_feat, f_type, params, doc5, part5)
                    logs.append(res_msg)
                    if not ok:
                        return False, res_msg, logs
                else:
                    cls = FEATURE_CLASSES.get(f_type)
                    if cls:
                        new_id = self._make_unique_id(f_type, f_id)
                        params["part_type"] = f_type
                        feat = cls(new_id, self.connector)
                        feat.feature_type = f_type
                        ok, res_msg = feat.build(params)
                        if ok:
                            self.features[new_id] = feat
                            self.feature_order.append(new_id)
                        logs.append(res_msg)
                        if not ok:
                            return False, res_msg, logs
                    else:
                        return False, f"Элемент {f_id} не найден для модификации.", logs

        return True, "Команды успешно выполнены", logs


engine = AzimutCadEngine()


class AzimutRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            self._send_json(engine.get_full_status())
        elif self.path == "/connect":
            ok, msg = engine.connector.connect()
            if ok:
                engine.connector.ensure_document()
            st = engine.get_full_status()
            st["message"] = msg
            self._send_json(st)
        elif self.path == "/disconnect":
            ok, msg = engine.connector.disconnect()
            st = engine.get_full_status()
            st["message"] = msg
            self._send_json(st)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(raw)
        except Exception as e:
            self._send_json({"success": False, "message": f"Ошибка JSON: {e}", "logs": []}, 400)
            return

        if self.path == "/execute":
            try:
                ok, msg, logs = engine.execute_commands(payload)
                st = engine.get_full_status()
                self._send_json({
                    "success": ok,
                    "message": msg,
                    "logs": logs,
                    "status": st
                })
            except Exception as e:
                tb = traceback.format_exc()
                self._send_json({
                    "success": False,
                    "message": f"Исключение Python: {str(e)}",
                    "logs": [tb]
                }, 500)
        else:
            self._send_json({"error": "Not found"}, 404)


def run_server(port=8765):
    server = HTTPServer(("127.0.0.1", port), AzimutRequestHandler)
    print(f"Python CAD Bridge Server started on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_server(port)