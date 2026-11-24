from features.base_feature import BaseFeature
from math_helper import MathHelper


class PlateFeature(BaseFeature):
    def _extract_dims(self, params):
        if self.feature_type == "cube" or "size" in params or "side" in params:
            s = float(params.get("size", params.get("side", params.get("width", params.get("length", params.get("height", params.get("thickness", 50.0)))))))
            return s, s, s
        w = float(params.get("width", params.get("w", 100.0)))
        l = float(params.get("length", params.get("l", w)))
        t = float(params.get("thickness", params.get("height", params.get("h", 10.0))))
        return w, l, t

    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        width, length, thickness = self._extract_dims(self.params)
        self.params["width"] = width
        self.params["length"] = length
        self.params["thickness"] = thickness
        z_offset = float(self.params.get("z_offset", 0.0))

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        x1, y1, x2, y2 = MathHelper.get_centered_rect(width, length)
        doc2d.ksLineSeg(x1, y1, x2, y1, 1)
        doc2d.ksLineSeg(x2, y1, x2, y2, 1)
        doc2d.ksLineSeg(x2, y2, x1, y2, 1)
        doc2d.ksLineSeg(x1, y2, x1, y1, 1)
        sketch_def.EndEdit()

        label = "Куб" if self.feature_type == "cube" else "Пластина"
        self._extrude_boss(sketch_ent, thickness, f"{label}_{self.feature_id}")
        return True, f"Построен элемент «{label}» ({width}x{length}x{thickness} мм)"