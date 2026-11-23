# src_python/features/holes_feature.py
from features.base_feature import BaseFeature
from math_helper import MathHelper


class CornerHolesFeature(BaseFeature):
    """Создание и редактирование 4 отверстий по углам на плоскости ZX"""

    def build(self, params: dict) -> bool:
        self.params = params
        w = float(params["plate_width"])
        l = float(params["plate_length"])
        d = float(params["diameter"])
        offset = float(params["offset"])

        plane = self.part.GetDefaultEntity(self.PLANE_XZ)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: Отверстия Ø{d:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_circles(sketch_def, w, l, d, offset)

        self.operation_entity = self._new_entity(self.OBJ_CUT_EXTRUDE)
        self.operation_entity.name = f"Отверстия по углам Ø{d:g} (отступ {offset:g})"
        cut_def = self.m5.ksCutExtrusionDefinition(self.operation_entity.GetDefinition())
        cut_def.SetSketch(self.sketch_entity)
        cut_def.SetSideParam(True, 1, 0, 0, False)
        cut_def.SetSideParam(False, 1, 0, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        w = float(self.params["plate_width"])
        l = float(self.params["plate_length"])
        d = float(self.params["diameter"])
        offset = float(params["offset"])

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_circles(sketch_def, w, l, d, offset)
        self.sketch_entity.name = f"Эскиз: Отверстия Ø{d:g}"
        self.sketch_entity.Update()

        self.operation_entity.name = f"Отверстия по углам Ø{d:g} (отступ {offset:g})"
        self.operation_entity.Update()
        self.part.Update()
        return True

    def _draw_circles(self, sketch_def, w: float, l: float, d: float, offset: float):
        sketch_edit = self.m5.ksDocument2D(sketch_def.BeginEdit())
        radius = d / 2.0
        for cx, cy in MathHelper.get_corner_holes(w, l, offset):
            sketch_edit.ksCircle(cx, cy, radius, 1)
        sketch_def.EndEdit()