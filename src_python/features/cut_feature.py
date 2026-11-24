import math
from features.base_feature import BaseFeature


class SingleHoleFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", self.params.get("d", 10.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        through = bool(self.params.get("through", True))
        depth = float(self.params.get("depth", self.params.get("h", 10.0)))
        z_offset = float(self.params.get("z_offset", 0.0))

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(cx, cy, diameter / 2.0, 1)
        sketch_def.EndEdit()

        self._extrude_cut(sketch_ent, depth, through, f"Отверстие_{self.feature_id}")
        mode_str = "сквозное" if through else f"глубина {depth} мм"
        return True, f"Выполнено отверстие Ø{diameter} мм ({mode_str})"


class CircularHolesFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        count = max(1, int(self.params.get("count", 6)))
        diameter = float(self.params.get("diameter", self.params.get("d", 8.0)))
        circle_d = float(self.params.get("circle_diameter", self.params.get("pitch_diameter", 60.0)))
        through = bool(self.params.get("through", True))
        depth = float(self.params.get("depth", 10.0))
        z_offset = float(self.params.get("z_offset", 0.0))

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        pitch_r = circle_d / 2.0
        hole_r = diameter / 2.0
        for i in range(count):
            ang = 2.0 * math.pi * i / count
            hx = pitch_r * math.cos(ang)
            hy = pitch_r * math.sin(ang)
            doc2d.ksCircle(hx, hy, hole_r, 1)
        sketch_def.EndEdit()

        self._extrude_cut(sketch_ent, depth, through, f"ОтверстияПоОкружности_{self.feature_id}")
        return True, f"Выполнено {count} отверстий Ø{diameter} мм по окружности Ø{circle_d} мм"


class CutBoxFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        width = float(self.params.get("width", self.params.get("w", 20.0)))
        length = float(self.params.get("length", self.params.get("l", 20.0)))
        depth = float(self.params.get("depth", self.params.get("height", 10.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        through = bool(self.params.get("through", False))
        z_offset = float(self.params.get("z_offset", 0.0))

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        hw = width / 2.0
        hl = length / 2.0
        x1, y1 = cx - hw, cy - hl
        x2, y2 = cx + hw, cy + hl
        doc2d.ksLineSeg(x1, y1, x2, y1, 1)
        doc2d.ksLineSeg(x2, y1, x2, y2, 1)
        doc2d.ksLineSeg(x2, y2, x1, y2, 1)
        doc2d.ksLineSeg(x1, y2, x1, y1, 1)
        sketch_def.EndEdit()

        self._extrude_cut(sketch_ent, depth, through, f"Вырез_{self.feature_id}")
        return True, f"Выполнен прямоугольный вырез {width}x{length} мм"