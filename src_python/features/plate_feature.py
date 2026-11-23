from features.base_feature import BaseFeature


class PlateFeature(BaseFeature):
    def _extract_dims(self, params: dict) -> tuple:
        size = params.get("size", params.get("side", None))
        if size is not None:
            s = float(size)
            w = float(params.get("width", s))
            l = float(params.get("length", s))
            h = float(params.get("height", params.get("thickness", s)))
        else:
            w = float(params.get("width", 100))
            l = float(params.get("length", w))
            h = float(params.get("thickness", params.get("height", 10)))
        cx = float(params.get("x", 0))
        cy = float(params.get("y", 0))
        z_offset = float(params.get("z_offset", 0))
        return w, l, h, cx, cy, z_offset

    def build(self, params: dict) -> bool:
        w, l, h, cx, cy, z_offset = self._extract_dims(params)
        self.params = {"width": w, "length": l, "thickness": h, "x": cx, "y": cy, "z_offset": z_offset}

        plane = self._get_work_plane(z_offset)
        self.sketch_entity = self._new_entity(self.OBJ_SKETCH)
        self.sketch_entity.name = f"Эскиз: База {w:g}x{l:g}"
        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        sketch_def.SetPlane(plane)
        self.sketch_entity.Create()

        self._draw_rect(sketch_def, cx, cy, w, l)

        self.operation_entity = self._new_entity(self.OBJ_BOSS_EXTRUDE)
        self.operation_entity.name = f"Параллелепипед {w:g}x{l:g}x{h:g}"
        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSketch(self.sketch_entity)
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        w, l, h, cx, cy, z_offset = self._extract_dims(self.params)
        self.params = {"width": w, "length": l, "thickness": h, "x": cx, "y": cy, "z_offset": z_offset}

        if abs(z_offset) > 1e-5:
            self._get_work_plane(z_offset)

        sketch_def = self.m5.ksSketchDefinition(self.sketch_entity.GetDefinition())
        self._draw_rect(sketch_def, cx, cy, w, l, clear_old=True)
        self.sketch_entity.name = f"Эскиз: База {w:g}x{l:g}"
        self.sketch_entity.Update()

        extrude_def = self.m5.ksBossExtrusionDefinition(self.operation_entity.GetDefinition())
        extrude_def.SetSideParam(True, 0, h, 0, False)
        self.operation_entity.name = f"Параллелепипед {w:g}x{l:g}x{h:g}"
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