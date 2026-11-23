import sys
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from kompas_connector import KompasConnector
from tree_scanner import TreeScanner
from features.plate_feature import PlateFeature
from features.holes_feature import CornerHolesFeature
from features.cylinder_feature import CylinderFeature, TubeFeature, PolygonPrismFeature, ConeFeature
from features.cut_feature import SingleHoleFeature, CircularHolesFeature, CutBoxFeature
from features.edge_feature import ChamferFeature, FilletFeature

sys.stdout.reconfigure(encoding='utf-8')


class AzimutCadEngine:
    FEATURE_MAP = {
        "plate": PlateFeature,
        "box": PlateFeature,
        "cube": PlateFeature,
        "corner_holes": CornerHolesFeature,
        "cylinder": CylinderFeature,
        "tube": TubeFeature,
        "polygon": PolygonPrismFeature,
        "cone": ConeFeature,
        "hole": SingleHoleFeature,
        "circle_holes": CircularHolesFeature,
        "cut_box": CutBoxFeature,
        "chamfer": ChamferFeature,
        "fillet": FilletFeature
    }

    BOSS_TYPES = {"plate", "box", "cube", "cylinder", "tube", "polygon", "cone"}

    def __init__(self):
        self.kompas = KompasConnector()
        self.scanner = TreeScanner(self.kompas)
        self.features = {}
        self.history_stack = []

    def _get_current_top_height(self) -> float:
        max_h = 0.0
        for fid, feat in self.features.items():
            p = feat.params
            z0 = float(p.get("z_offset", 0))
            h = float(p.get("thickness", p.get("height", 0)))
            if h > 0 and (z0 + h) > max_h:
                max_h = z0 + h
        return max_h

    def _get_base_plate_dims(self) -> tuple:
        for fid, feat in self.features.items():
            if "width" in feat.params and "length" in feat.params:
                return float(feat.params["width"]), float(feat.params["length"])
        return 100.0, 50.0

    def _find_target_id(self, feat_id: str, feat_type: str) -> str:
        if feat_id and feat_id in self.features:
            return feat_id
        if feat_type and feat_type in self.features:
            return feat_type
        for k in reversed(self.history_stack):
            if feat_type and k.startswith(feat_type):
                return k
        return ""

    def get_status(self) -> dict:
        if not self.kompas.is_connected:
            return {"indicator": "red", "text": "Отключено от КОМПАС-3D", "context": {}}

        has_doc = self.kompas._check_active_doc()
        if not has_doc:
            return {"indicator": "yellow", "text": "КОМПАС открыт (нет 3D-детали)", "context": {}}

        return {
            "indicator": "green",
            "text": "Подключено к 3D-детали (.m3d)",
            "context": self.scanner.get_compact_tree(self.features)
        }

    def execute_batch(self, payload: dict) -> dict:
        if not self.kompas.is_connected:
            res = self.kompas.connect()
            if res["status"] != "connected":
                return {"status": "error", "message": "Не удалось подключиться к КОМПАС-3D"}

        self.kompas.ensure_part_document()
        commands = payload.get("commands", [payload])
        results = []

        for cmd in commands:
            action = cmd.get("action")
            feat_type = cmd.get("type", "")
            feat_id = cmd.get("id", feat_type)
            params = cmd.get("params", {})

            try:
                if action == "build":
                    if feat_type not in self.FEATURE_MAP:
                        return {"status": "error", "message": f"Неизвестный тип операции: {feat_type}"}

                    if feat_type == "corner_holes":
                        bw, bl = self._get_base_plate_dims()
                        params.setdefault("plate_width", bw)
                        params.setdefault("plate_length", bl)

                    if feat_type in self.BOSS_TYPES and len(self.features) > 0:
                        if float(params.get("z_offset", 0)) == 0.0:
                            params["z_offset"] = self._get_current_top_height()

                    if feat_type in ("hole", "cut_box") and float(params.get("depth", 0)) > 0:
                        params["z_offset"] = self._get_current_top_height()

                    if feat_id in self.features:
                        feat_id = f"{feat_type}_{len(self.features) + 1}"

                    feat_cls = self.FEATURE_MAP[feat_type]
                    feat = feat_cls(feat_id, self.kompas)
                    feat.build(params)
                    self.features[feat_id] = feat
                    self.history_stack.append(feat_id)
                    results.append(f"построено {feat_id}")

                elif action == "update":
                    target_id = self._find_target_id(feat_id, feat_type)
                    if not target_id:
                        return {"status": "error", "message": f"Элемент {feat_id} не найден"}
                    self.features[target_id].update(params)
                    if target_id in ("plate", "box", "cube") and "corner_holes" in self.features:
                        bw, bl = self._get_base_plate_dims()
                        self.features["corner_holes"].update({
                            "plate_width": bw,
                            "plate_length": bl
                        })
                    results.append(f"обновлено {target_id}")

                elif action == "undo":
                    if not self.history_stack:
                        return {"status": "error", "message": "История шагов пуста, отменять нечего"}
                    last_id = self.history_stack.pop()
                    if last_id in self.features:
                        self.features[last_id].delete()
                        del self.features[last_id]
                    results.append(f"отменен шаг {last_id}")

                elif action == "delete":
                    target_id = self._find_target_id(feat_id, feat_type)
                    if not target_id:
                        return {"status": "error", "message": f"Элемент {feat_id} не найден для удаления"}
                    self.features[target_id].delete()
                    del self.features[target_id]
                    if target_id in self.history_stack:
                        self.history_stack.remove(target_id)
                    results.append(f"удалено {target_id}")

                elif action == "clear":
                    for fid in reversed(list(self.history_stack)):
                        if fid in self.features:
                            self.features[fid].delete()
                    self.features.clear()
                    self.history_stack.clear()
                    results.append("деталь полностью очищена")

            except Exception as e:
                return {"status": "error", "message": f"Ошибка выполнения: {str(e)}"}

        return {
            "status": "ok",
            "message": "Выполнено: " + ", ".join(results),
            "context": self.scanner.get_compact_tree(self.features)
        }


engine = AzimutCadEngine()


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            self._send_json(engine.get_status())
        else:
            self._send_json({"status": "error", "message": "Не найдено"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if self.path == "/connect":
            res = engine.kompas.connect()
            if res["status"] == "connected":
                engine.kompas.ensure_part_document()
                engine.kompas.bring_to_front()
            self._send_json(engine.get_status())

        elif self.path == "/disconnect":
            engine.kompas.is_connected = False
            self._send_json(engine.get_status())

        elif self.path == "/execute":
            res = engine.execute_batch(body)
            self._send_json(res)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8765), RequestHandler)
    print("Сервер АЗИМУТ запущен: http://127.0.0.1:8765", flush=True)
    server.serve_forever()