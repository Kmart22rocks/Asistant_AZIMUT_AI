import pythoncom
from features.base_feature import BaseFeature
class CounterboreFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        d_hole = float(self.params.get("diameter", 10.0))
        d_cb = float(self.params.get("cb_diameter", self.params.get("head_diameter", d_hole * 1.8)))
        h_cb = float(self.params.get("cb_depth", self.params.get("head_depth", 6.0)))
        depth = float(self.params.get("depth", 30.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизЦековки_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        r1 = d_hole / 2.0
        r2 = d_cb / 2.0
        y_top = y_offset
        y_mid = y_offset - h_cb
        y_bot = y_offset - depth
        doc2d.ksLineSeg(0.0, y_top, r2, y_top, 1)
        doc2d.ksLineSeg(r2, y_top, r2, y_mid, 1)
        doc2d.ksLineSeg(r2, y_mid, r1, y_mid, 1)
        doc2d.ksLineSeg(r1, y_mid, r1, y_bot, 1)
        doc2d.ksLineSeg(r1, y_bot, 0.0, y_bot, 1)
        doc2d.ksLineSeg(0.0, y_bot, 0.0, y_top, 1)
        doc2d.ksLineSeg(0.0, y_bot, 0.0, y_top, 3)
        sketch_def.EndEdit()
        cut_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cutRotated))
        cut_def = self.m5.ksCutRotatedDefinition(
            cut_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksCutRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        cut_def.directionType = self.const.dtNormal
        cut_def.SetSideParam(True, 360.0)
        cut_def.SetSketch(sketch_ent)
        cut_ent.name = f"Цековка_{self.feature_id}"
        cut_ent.Create()
        self.operation_entity = cut_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Выполнено отверстие Ø{d_hole} с цековкой Ø{d_cb}x{h_cb} мм"
class CountersinkFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        d_hole = float(self.params.get("diameter", 10.0))
        d_cs = float(self.params.get("cs_diameter", self.params.get("head_diameter", d_hole * 2.0)))
        h_cs = float(self.params.get("cs_depth", (d_cs - d_hole) / 2.0))
        depth = float(self.params.get("depth", 30.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизЗенковки_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        r1 = d_hole / 2.0
        r2 = d_cs / 2.0
        y_top = y_offset
        y_mid = y_offset - h_cs
        y_bot = y_offset - depth
        doc2d.ksLineSeg(0.0, y_top, r2, y_top, 1)
        doc2d.ksLineSeg(r2, y_top, r1, y_mid, 1)
        doc2d.ksLineSeg(r1, y_mid, r1, y_bot, 1)
        doc2d.ksLineSeg(r1, y_bot, 0.0, y_bot, 1)
        doc2d.ksLineSeg(0.0, y_bot, 0.0, y_top, 1)
        doc2d.ksLineSeg(0.0, y_bot, 0.0, y_top, 3)
        sketch_def.EndEdit()
        cut_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cutRotated))
        cut_def = self.m5.ksCutRotatedDefinition(
            cut_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksCutRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        cut_def.directionType = self.const.dtNormal
        cut_def.SetSideParam(True, 360.0)
        cut_def.SetSketch(sketch_ent)
        cut_ent.name = f"Зенковка_{self.feature_id}"
        cut_ent.Create()
        self.operation_entity = cut_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Выполнено отверстие Ø{d_hole} с зенковкой Ø{d_cs} мм"
class GrooveFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        outer_d = float(self.params.get("diameter", 40.0))
        groove_d = float(self.params.get("groove_diameter", outer_d - 6.0))
        width = float(self.params.get("width", 4.0))
        y_pos = float(self.params.get("y_offset", self.params.get("z_offset", 15.0)))
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизКанавки_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        r_in = min(outer_d, groove_d) / 2.0
        r_out = max(outer_d, groove_d) / 2.0 + 1.0
        y1 = y_pos - width / 2.0
        y2 = y_pos + width / 2.0
        doc2d.ksLineSeg(r_in, y1, r_out, y1, 1)
        doc2d.ksLineSeg(r_out, y1, r_out, y2, 1)
        doc2d.ksLineSeg(r_out, y2, r_in, y2, 1)
        doc2d.ksLineSeg(r_in, y2, r_in, y1, 1)
        doc2d.ksLineSeg(0.0, y1 - 5.0, 0.0, y2 + 5.0, 3)
        sketch_def.EndEdit()
        cut_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cutRotated))
        cut_def = self.m5.ksCutRotatedDefinition(
            cut_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksCutRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        cut_def.directionType = self.const.dtNormal
        cut_def.SetSideParam(True, 360.0)
        cut_def.SetSketch(sketch_ent)
        cut_ent.name = f"Канавка_{self.feature_id}"
        cut_ent.Create()
        self.operation_entity = cut_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Выполнена кольцевая проточка Ø{groove_d} мм, ширина {width} мм"
class CrossSlotFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        length = float(self.params.get("length", 30.0))
        width = float(self.params.get("width", 6.0))
        depth = float(self.params.get("depth", 5.0))
        through = bool(self.params.get("through", False))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        hl = length / 2.0
        hw = width / 2.0
        pts = [
            (cx - hw, cz - hl), (cx + hw, cz - hl),
            (cx + hw, cz - hw), (cx + hl, cz - hw),
            (cx + hl, cz + hw), (cx + hw, cz + hw),
            (cx + hw, cz + hl), (cx - hw, cz + hl),
            (cx - hw, cz + hw), (cx - hl, cz + hw),
            (cx - hl, cz - hw), (cx - hw, cz - hw)
        ]
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        self._extrude_cut(sketch_ent, depth, through, f"КрестПаз_{self.feature_id}")
        return True, f"Выполнен крестообразный паз {length}x{width} мм, глубина {depth} мм"
class TSlotFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        neck_w = float(self.params.get("neck_width", self.params.get("width", 10.0)))
        base_w = float(self.params.get("base_width", neck_w * 1.8))
        total_h = float(self.params.get("depth", 16.0))
        base_h = float(self.params.get("base_depth", total_h * 0.45))
        length = float(self.params.get("length", 100.0))
        y_top = float(self.params.get("y_offset", self.params.get("z_offset", 20.0)))
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизТПаза_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        hn = neck_w / 2.0
        hb = base_w / 2.0
        ym = y_top - (total_h - base_h)
        yb = y_top - total_h
        pts = [
            (-hn, y_top), (hn, y_top),
            (hn, ym), (hb, ym),
            (hb, yb), (-hb, yb),
            (-hb, ym), (-hn, ym)
        ]
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        cut_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cutExtrusion))
        cut_def = self.m5.ksCutExtrusionDefinition(
            cut_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksCutExtrusionDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        cut_def.directionType = self.const.dtMiddlePlane
        cut_def.SetSideParam(True, self.const.etBlind, length, 0.0, False)
        cut_def.SetSketch(sketch_ent)
        cut_ent.name = f"ТПаз_{self.feature_id}"
        cut_ent.Create()
        self.operation_entity = cut_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Выполнен Т-образный паз {neck_w}/{base_w}x{total_h} мм"