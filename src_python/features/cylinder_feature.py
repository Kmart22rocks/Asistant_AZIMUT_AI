import math
from features.base_feature import BaseFeature


class CylinderFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", self.params.get("d", float(self.params.get("radius", 15.0)) * 2.0)))
        height = float(self.params.get("height", self.params.get("h", 30.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        z_offset = float(self.params.get("z_offset", 0.0))
        self.params["diameter"] = diameter
        self.params["height"] = height

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(cx, cy, diameter / 2.0, 1)
        sketch_def.EndEdit()

        self._extrude_boss(sketch_ent, height, f"Цилиндр_{self.feature_id}")
        return True, f"Построен цилиндр Ø{diameter} мм, высота {height} мм"


class TubeFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        outer_d = float(self.params.get("outer_diameter", self.params.get("diameter", 40.0)))
        inner_d = float(self.params.get("inner_diameter", outer_d * 0.6))
        if inner_d >= outer_d:
            inner_d = outer_d * 0.5
        height = float(self.params.get("height", self.params.get("h", 40.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        z_offset = float(self.params.get("z_offset", 0.0))
        self.params["outer_diameter"] = outer_d
        self.params["inner_diameter"] = inner_d
        self.params["height"] = height

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(cx, cy, outer_d / 2.0, 1)
        doc2d.ksCircle(cx, cy, inner_d / 2.0, 1)
        sketch_def.EndEdit()

        self._extrude_boss(sketch_ent, height, f"Труба_{self.feature_id}")
        return True, f"Построена труба Ø{outer_d}/Ø{inner_d} мм, высота {height} мм"


class PolygonPrismFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        sides = max(3, int(self.params.get("sides", self.params.get("count", 6))))
        diameter = float(self.params.get("diameter", self.params.get("d", 40.0)))
        height = float(self.params.get("height", self.params.get("h", 25.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        z_offset = float(self.params.get("z_offset", 0.0))
        self.params["sides"] = sides
        self.params["diameter"] = diameter
        self.params["height"] = height

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        radius = diameter / 2.0
        start_angle = math.pi / sides
        pts = []
        for i in range(sides):
            ang = start_angle + 2.0 * math.pi * i / sides
            pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
        for i in range(sides):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % sides]
            doc2d.ksLineSeg(x1, y1, x2, y2, 1)
        sketch_def.EndEdit()

        self._extrude_boss(sketch_ent, height, f"Призма_{self.feature_id}")
        return True, f"Построена {sides}-гранная призма Ø{diameter} мм, высота {height} мм"


class ConeFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        base_d = float(self.params.get("diameter", self.params.get("base_diameter", 40.0)))
        top_d = float(self.params.get("top_diameter", 0.0))
        height = float(self.params.get("height", self.params.get("h", 40.0)))
        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("y", 0.0))
        z_offset = float(self.params.get("z_offset", 0.0))
        self.params["diameter"] = base_d
        self.params["height"] = height

        if top_d < 0.2:
            top_d = 0.2
        r_diff = (base_d - top_d) / 2.0
        draft_angle = math.degrees(math.atan2(abs(r_diff), height))
        draft_outward = top_d > base_d

        plane = self._get_work_plane(z_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(cx, cy, base_d / 2.0, 1)
        sketch_def.EndEdit()

        self._extrude_boss(sketch_ent, height, f"Конус_{self.feature_id}", draft_angle=draft_angle, draft_outward=draft_outward)
        return True, f"Построен конус Ø{base_d} мм, высота {height} мм"