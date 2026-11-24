from features.base_feature import BaseFeature
from math_helper import MathHelper


class CornerHolesFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", self.params.get("d", 10.0)))
        offset = float(self.params.get("offset", 15.0))
        plate_w = float(self.params.get("plate_width", self.params.get("width", 100.0)))
        plate_l = float(self.params.get("plate_length", self.params.get("length", 100.0)))
        z_offset = float(self.params.get("z_offset", 0.0))

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        radius = diameter / 2.0
        centers = MathHelper.get_corner_holes(plate_w, plate_l, offset)
        for cx, cy in centers:
            doc2d.ksCircle(cx, cy, radius, 1)
        sketch_def.EndEdit()

        self._extrude_cut(sketch_ent, 0.0, True, f"ОтверстияУгловые_{self.feature_id}")
        return True, f"Выполнены 4 угловых отверстия Ø{diameter} мм (отступ {offset} мм)"