import math
from features.base_feature import BaseFeature


class SingleHoleFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        d = float(params.get("diameter", 10))
        depth = float(params.get("depth", 0))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset if depth > 0 else 0)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Отверстие Ø{d:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_hole(sketch_def, cx, cy, d)

        self.operation_entity = self._new_entity(self.OBJ_CUT_EXTRUDE)
        self.operation_entity.name = f"Отверстие Ø{d:g} ({cx:g}; {cy:g})"
        cut_def = self.m5.ksCutExtrusionDefinition(self.operation_entity.GetDefinition())
        cut_def.SetSketch(self.sketch_entity)
        if depth <= 0:
            cut_def.SetSideParam(True, 1, 0, 0, False)
            cut_def.SetSideParam(False, 1, 0, 0, False)
        else:
            cut_def.SetSideParam(False, 0, depth, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        d = float(self.params.get("diameter", 10))
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_hole(sketch_def, cx, cy, d, clear_old=True)
        self.sketch_entity.Update()
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_hole(self, sketch_def, cx: float, cy: float, d: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        sketch_edit.ksCircle(cx, cy, d / 2.0, 1)
        sketch_def.EndEdit()


class CircularHolesFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        count = int(params.get("count", 6))
        d = float(params.get("diameter", 8))
        circle_d = float(params.get("circle_diameter", 60))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))

        plane = self.part.GetDefaultEntity(self.DEFAULT_PLANE)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: {count} отв. Ø{d:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_pattern(sketch_def, cx, cy, count, d, circle_d)

        self.operation_entity = self._new_entity(self.OBJ_CUT_EXTRUDE)
        self.operation_entity.name = f"Массив {count} отв. Ø{d:g} на Ø{circle_d:g}"
        cut_def = self.m5.ksCutExtrusionDefinition(self.operation_entity.GetDefinition())
        cut_def.SetSketch(self.sketch_entity)
        cut_def.SetSideParam(True, 1, 0, 0, False)
        cut_def.SetSideParam(False, 1, 0, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        count = int(self.params.get("count", 6))
        d = float(self.params.get("diameter", 8))
        circle_d = float(self.params.get("circle_diameter", 60))
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_pattern(sketch_def, cx, cy, count, d, circle_d, clear_old=True)
        self.sketch_entity.Update()
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_pattern(self, sketch_def, cx: float, cy: float, count: int, d: float, circle_d: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        R = circle_d / 2.0
        r = d / 2.0
        for i in range(count):
            ang = 2.0 * math.pi * i / count
            sketch_edit.ksCircle(cx + R * math.cos(ang), cy + R * math.sin(ang), r, 1)
        sketch_def.EndEdit()


class CutBoxFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        w = float(params.get("width", 20))
        l = float(params.get("length", 20))
        depth = float(params.get("depth", 0))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))

        plane = self._get_work_plane(z_offset if depth > 0 else 0)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Паз {w:g}x{l:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_rect(sketch_def, cx, cy, w, l)

        self.operation_entity = self._new_entity(self.OBJ_CUT_EXTRUDE)
        self.operation_entity.name = f"Вырез {w:g}x{l:g}"
        cut_def = self.m5.ksCutExtrusionDefinition(self.operation_entity.GetDefinition())
        cut_def.SetSketch(self.sketch_entity)
        if depth <= 0:
            cut_def.SetSideParam(True, 1, 0, 0, False)
            cut_def.SetSideParam(False, 1, 0, 0, False)
        else:
            cut_def.SetSideParam(False, 0, depth, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        w = float(self.params["width"])
        l = float(self.params["length"])
        cx = float(self.params.get("x", 0))
        cy = float(self.params.get("y", 0))

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_rect(sketch_def, cx, cy, w, l, clear_old=True)
        self.sketch_entity.Update()
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_rect(self, sketch_def, cx: float, cy: float, w: float, l: float, clear_old=False):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        if clear_old:
            sketch_edit.ksDeleteObj(0)
        x1, y1 = cx - w / 2.0, cy - l / 2.0
        x2, y2 = cx + w / 2.0, cy + l / 2.0
        sketch_edit.ksLineSeg(x1, y1, x2, y1, 1)
        sketch_edit.ksLineSeg(x2, y1, x2, y2, 1)
        sketch_edit.ksLineSeg(x2, y2, x1, y2, 1)
        sketch_edit.ksLineSeg(x1, y2, x1, y1, 1)
        sketch_def.EndEdit()