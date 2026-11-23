import math
from features.base_feature import BaseFeature


class CylinderFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        d = float(params.get("diameter", 30))
        h = float(params.get("height", params.get("thickness", 50)))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Цилиндр Ø{d:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_circle(sketch_def, cx, cy, d)

        self.operation_entity = self._new_entity(self.OBJ_BOSS_EXTRUDE)
        self.operation_entity.name = f"Цилиндр Ø{d:g}x{h:g}"
        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSketch(self.sketch_entity)
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        d = float(self.params.get("diameter", 30))
        h = float(self.params.get("height", self.params.get("thickness", 50)))
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))
        z_offset = float(self.params.get("z_offset", 0))

        if abs(z_offset) > 1e-5:
            self._get_work_plane(z_offset)

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_circle(sketch_def, cx, cy, d, clear_old=True)
        self.sketch_entity.name = f"Эскиз: Цилиндр Ø{d:g}"
        self.sketch_entity.Update()

        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.name = f"Цилиндр Ø{d:g}x{h:g}"
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_circle(self, sketch_def, cx: float, cy: float, d: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        sketch_edit.ksCircle(cx, cy, d / 2.0, 1)
        sketch_def.EndEdit()


class TubeFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        d_out = float(params.get("outer_diameter", 40))
        d_in = float(params.get("inner_diameter", 20))
        h = float(params.get("height", 50))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Втулка Ø{d_out:g}/Ø{d_in:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_rings(sketch_def, cx, cy, d_out, d_in)

        self.operation_entity = self._new_entity(self.OBJ_BOSS_EXTRUDE)
        self.operation_entity.name = f"Втулка Ø{d_out:g}x{h:g}"
        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSketch(self.sketch_entity)
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        d_out = float(self.params["outer_diameter"])
        d_in = float(self.params["inner_diameter"])
        h = float(self.params["height"])
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))
        z_offset = float(self.params.get("z_offset", 0))

        if abs(z_offset) > 1e-5:
            self._get_work_plane(z_offset)

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_rings(sketch_def, cx, cy, d_out, d_in, clear_old=True)
        self.sketch_entity.Update()

        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_rings(self, sketch_def, cx: float, cy: float, d_out: float, d_in: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        sketch_edit.ksCircle(cx, cy, d_out / 2.0, 1)
        sketch_edit.ksCircle(cx, cy, d_in / 2.0, 1)
        sketch_def.EndEdit()


class PolygonPrismFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        sides = int(params.get("sides", 6))
        d = float(params.get("diameter", params.get("size", 30)))
        h = float(params.get("height", params.get("thickness", 20)))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Многогранник ({sides} гр.)"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_polygon(sketch_def, cx, cy, sides, d / 2.0)

        self.operation_entity = self._new_entity(self.OBJ_BOSS_EXTRUDE)
        self.operation_entity.name = f"Призма {sides}-гранная В={h:g}"
        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSketch(self.sketch_entity)
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        sides = int(self.params.get("sides", 6))
        d = float(self.params.get("diameter", self.params.get("size", 30)))
        h = float(self.params.get("height", self.params.get("thickness", 20)))
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))
        z_offset = float(self.params.get("z_offset", 0))

        if abs(z_offset) > 1e-5:
            self._get_work_plane(z_offset)

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_polygon(sketch_def, cx, cy, sides, d / 2.0, clear_old=True)
        self.sketch_entity.Update()

        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_polygon(self, sketch_def, cx: float, cy: float, sides: int, radius: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        pts = []
        start_angle = math.pi / sides
        for i in range(sides):
            ang = (2.0 * math.pi * i / sides) + start_angle
            pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
        for i in range(sides):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % sides]
            sketch_edit.ksLineSeg(x1, y1, x2, y2, 1)
        sketch_def.EndEdit()


class ConeFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        d_base = float(params.get("base_diameter", params.get("diameter", 40)))
        d_top = float(params.get("top_diameter", 0))
        h = float(params.get("height", 50))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Конус Ø{d_base:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        sketch_edit.ksCircle(cx, cy, d_base / 2.0, 1)
        sketch_def.EndEdit()

        draft_rad = math.atan2(abs(d_base - d_top) / 2.0, h)
        draft_deg = math.degrees(draft_rad)
        outward = d_top > d_base

        self.operation_entity = self._new_entity(self.OBJ_BOSS_EXTRUDE)
        self.operation_entity.name = f"Конус Ø{d_base:g}x{h:g}"
        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSketch(self.sketch_entity)
        extrude_def.SetSideParam(True, 0, h, draft_deg, outward)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        return self.build(self.params)