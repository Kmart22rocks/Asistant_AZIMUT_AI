import math
import pythoncom
from features.base_feature import BaseFeature
class TorusFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        major_d = float(self.params.get("diameter", self.params.get("major_diameter", 60.0)))
        minor_d = float(self.params.get("tube_diameter", self.params.get("minor_diameter", 12.0)))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = minor_d
        self.params["z_offset"] = y_offset
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизТора_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        R = max(minor_d * 0.6, major_d / 2.0)
        r = minor_d / 2.0
        doc2d.ksCircle(R, y_offset, r, 1)
        doc2d.ksLineSeg(0.0, y_offset - r * 2.0, 0.0, y_offset + r * 2.0, 3)
        sketch_def.EndEdit()
        rot_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossRotated))
        rot_def = self.m5.ksBossRotatedDefinition(
            rot_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksBossRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        rot_def.directionType = self.const.dtNormal
        rot_def.SetSideParam(True, 360.0)
        rot_def.SetSketch(sketch_ent)
        rot_ent.name = f"Тор_{self.feature_id}"
        rot_ent.Create()
        self.operation_entity = rot_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Построен тор Ø{major_d}x{minor_d} мм"
class DomeFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", 50.0))
        r = diameter / 2.0
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        dir_sign = -1 if float(self.params.get("direction", 1)) < 0 else 1
        self.params["height"] = r
        self.params["z_offset"] = y_offset
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизКупола_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        top_y = y_offset + dir_sign * r
        arc_mid = r * 0.70710678
        doc2d.ksLineSeg(0.0, y_offset, r, y_offset, 1)
        doc2d.ksLineSeg(0.0, y_offset, 0.0, top_y, 1)
        doc2d.ksArcBy3Points(r, y_offset, arc_mid, y_offset + dir_sign * arc_mid, 0.0, top_y, 1)
        doc2d.ksLineSeg(0.0, y_offset, 0.0, top_y, 3)
        sketch_def.EndEdit()
        rot_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossRotated))
        rot_def = self.m5.ksBossRotatedDefinition(
            rot_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksBossRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        rot_def.directionType = self.const.dtNormal
        rot_def.SetSideParam(True, 360.0)
        rot_def.SetSketch(sketch_ent)
        rot_ent.name = f"Купол_{self.feature_id}"
        rot_ent.Create()
        self.operation_entity = rot_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Построен купол Ø{diameter} мм (высота {r} мм)"
class SpringFeature(BaseFeature):
    def __init__(self, feature_id, kompas_connector):
        super().__init__(feature_id, kompas_connector)
        self.spiral_entity = None
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        mean_d = float(self.params.get("diameter", 40.0))
        wire_d = float(self.params.get("wire_diameter", self.params.get("d", 5.0)))
        turns = float(self.params.get("turns", self.params.get("count", 5.0)))
        pitch = float(self.params.get("pitch", self.params.get("step", wire_d * 2.2)))
        height = float(self.params.get("height", turns * pitch))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = height
        self.params["z_offset"] = y_offset
        plane = self._get_work_plane(y_offset)
        sp_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cylindricSpiral))
        sp_def = self.m5.ksCylindricSpiralDefinition(
            sp_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksCylindricSpiralDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        sp_def.SetPlane(plane)
        sp_def.buildDir = True
        sp_def.buildMode = 2
        sp_def.turn = turns
        sp_def.height = height
        sp_def.initialDiam = mean_d
        sp_def.terminalDiam = mean_d
        sp_def.SetLocation(0.0, 0.0)
        sp_ent.name = f"Спираль_{self.feature_id}"
        sp_ent.hidden = True
        sp_ent.Create()
        self.spiral_entity = sp_ent
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизПружины_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(mean_d / 2.0, y_offset, wire_d / 2.0, 1)
        sketch_def.EndEdit()
        evol_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossEvolution))
        evol_def = self.m5.ksBossEvolutionDefinition(
            evol_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksBossEvolutionDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        evol_def.SetSketch(sketch_ent)
        raw_arr = evol_def.PathPartArray()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )
        arr.Add(sp_ent)
        evol_ent.name = f"Пружина_{self.feature_id}"
        ok = evol_ent.Create()
        self.operation_entity = evol_ent
        self.part.Update()
        self.part.RebuildModel()
        if not ok:
            return False, "Не удалось построить пружину (проверьте шаг и диаметр витка)"
        return True, f"Построена пружина Ø{mean_d} мм, пруток Ø{wire_d} мм, витков: {turns}"
    def delete(self):
        if self.spiral_entity is not None:
            try:
                if self.doc3d:
                    self.doc3d.DeleteObject(self.spiral_entity)
            except Exception:
                pass
            try:
                self.spiral_entity.Delete()
            except Exception:
                pass
            self.spiral_entity = None
        return super().delete()
class GearFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        teeth = max(6, int(self.params.get("teeth", self.params.get("count", 16))))
        module = float(self.params.get("module", self.params.get("m", 3.0)))
        pitch_d = float(self.params.get("diameter", teeth * module))
        module = pitch_d / teeth
        height = float(self.params.get("height", self.params.get("thickness", 15.0)))
        bore_d = float(self.params.get("bore_diameter", self.params.get("inner_diameter", pitch_d * 0.3)))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["diameter"] = pitch_d + 2.0 * module
        self.params["height"] = height
        self.params["z_offset"] = y_offset
        r_outer = (pitch_d / 2.0) + module
        r_root = max(bore_d / 2.0 + 1.0, (pitch_d / 2.0) - 1.25 * module)
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        pts = []
        step_ang = 2.0 * math.pi / teeth
        for i in range(teeth):
            a0 = i * step_ang
            a1 = a0 + step_ang * 0.18
            a2 = a0 + step_ang * 0.32
            a3 = a0 + step_ang * 0.50
            pts.append((cx + r_root * math.cos(a0), cz + r_root * math.sin(a0)))
            pts.append((cx + r_outer * math.cos(a1), cz + r_outer * math.sin(a1)))
            pts.append((cx + r_outer * math.cos(a2), cz + r_outer * math.sin(a2)))
            pts.append((cx + r_root * math.cos(a3), cz + r_root * math.sin(a3)))
        n = len(pts)
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        if bore_d > 0.5:
            doc2d.ksCircle(cx, cz, bore_d / 2.0, 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, height, f"Шестерня_{self.feature_id}")
        return True, f"Построено зубчатое колесо (Z={teeth}, m={round(module, 2)}, ширина {height} мм)"
class FlangeFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        outer_d = float(self.params.get("outer_diameter", self.params.get("diameter", 120.0)))
        bore_d = float(self.params.get("inner_diameter", self.params.get("bore_diameter", 40.0)))
        thickness = float(self.params.get("thickness", self.params.get("height", 14.0)))
        holes_cnt = int(self.params.get("holes_count", self.params.get("count", 6)))
        hole_d = float(self.params.get("hole_diameter", 12.0))
        pitch_d = float(self.params.get("circle_diameter", (outer_d + bore_d) / 2.0))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["diameter"] = outer_d
        self.params["height"] = thickness
        self.params["z_offset"] = y_offset
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksCircle(cx, cz, outer_d / 2.0, 1)
        if bore_d > 0.5:
            doc2d.ksCircle(cx, cz, bore_d / 2.0, 1)
        pitch_r = pitch_d / 2.0
        for i in range(holes_cnt):
            ang = 2.0 * math.pi * i / holes_cnt
            doc2d.ksCircle(cx + pitch_r * math.cos(ang), cz + pitch_r * math.sin(ang), hole_d / 2.0, 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, thickness, f"Фланец_{self.feature_id}")
        return True, f"Построен фланец Ø{outer_d}/Ø{bore_d} мм, высота {thickness} мм ({holes_cnt} отв. Ø{hole_d})"
class RibFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        length = float(self.params.get("length", 40.0))
        height = float(self.params.get("height", 40.0))
        thickness = float(self.params.get("thickness", self.params.get("width", 8.0)))
        cx = float(self.params.get("x", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = height
        self.params["z_offset"] = y_offset
        plane_xy = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизРебра_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)
        doc2d.ksLineSeg(cx, y_offset, cx + length, y_offset, 1)
        doc2d.ksLineSeg(cx + length, y_offset, cx, y_offset + height, 1)
        doc2d.ksLineSeg(cx, y_offset + height, cx, y_offset, 1)
        sketch_def.EndEdit()
        extr_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossExtrusion))
        extr_def = self.m5.ksBossExtrusionDefinition(
            extr_ent.GetDefinition()._oleobj_.QueryInterface(self.m5.ksBossExtrusionDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        extr_def.directionType = self.const.dtMiddlePlane
        extr_def.SetSideParam(True, self.const.etBlind, thickness, 0.0, False)
        extr_def.SetSketch(sketch_ent)
        extr_ent.name = f"РеброЖесткости_{self.feature_id}"
        extr_ent.Create()
        self.operation_entity = extr_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Построено ребро жёсткости {length}x{height}x{thickness} мм"