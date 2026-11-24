import math
import pythoncom
from features.base_feature import BaseFeature


class CustomProfileFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        points = self.params.get("points", [[-30, -20], [30, -20], [20, 20], [-20, 20]])
        height = float(self.params.get("height", self.params.get("thickness", self.params.get("depth", 15.0))))
        is_cut = bool(self.params.get("is_cut", False))
        through = bool(self.params.get("through", False))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = height
        self.params["z_offset"] = y_offset

        if len(points) < 3:
            return False, "Для построения профиля необходимо минимум 3 точки."

        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]
            doc2d.ksLineSeg(float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1]), 1)
        sketch_def.EndEdit()

        if is_cut:
            self._extrude_cut(sketch_ent, height, through, f"ВырезПрофиля_{self.feature_id}")
            return True, f"Выполнен вырез по профилю ({n} точек)"
        else:
            self._extrude_boss(sketch_ent, height, f"Профиль_{self.feature_id}")
            return True, f"Построен профиль ({n} точек, высота {height} мм)"


class SlotFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        length = float(self.params.get("length", self.params.get("l", 40.0)))
        width = float(self.params.get("width", self.params.get("w", 10.0)))
        depth = float(self.params.get("depth", self.params.get("height", 10.0)))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", self.params.get("y", 0.0)))
        angle_deg = float(self.params.get("angle", 0.0))
        is_cut = bool(self.params.get("is_cut", True))
        through = bool(self.params.get("through", False))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["z_offset"] = y_offset

        r = width / 2.0
        straight = max(0.0, length - width)
        half_s = straight / 2.0
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        def rot(px, pz):
            return (cx + px * cos_a - pz * sin_a, cz + px * sin_a + pz * cos_a)

        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        if straight < 1e-4:
            doc2d.ksCircle(cx, cz, r, 1)
        else:
            p_tl = rot(-half_s, r)
            p_tr = rot(half_s, r)
            p_bl = rot(-half_s, -r)
            p_br = rot(half_s, -r)
            p_ml = rot(-half_s - r, 0.0)
            p_mr = rot(half_s + r, 0.0)

            doc2d.ksLineSeg(p_tl[0], p_tl[1], p_tr[0], p_tr[1], 1)
            doc2d.ksLineSeg(p_bl[0], p_bl[1], p_br[0], p_br[1], 1)
            doc2d.ksArcBy3Points(p_tl[0], p_tl[1], p_ml[0], p_ml[1], p_bl[0], p_bl[1], 1)
            doc2d.ksArcBy3Points(p_tr[0], p_tr[1], p_mr[0], p_mr[1], p_br[0], p_br[1], 1)
        sketch_def.EndEdit()

        if is_cut:
            self._extrude_cut(sketch_ent, depth, through, f"Паз_{self.feature_id}")
            return True, f"Выполнен паз {length}x{width} мм, глубина {depth} мм"
        else:
            self._extrude_boss(sketch_ent, depth, f"ВыступПаз_{self.feature_id}")
            return True, f"Построен выступ-паз {length}x{width}x{depth} мм"


class SphereFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", self.params.get("d", float(self.params.get("radius", 20.0)) * 2.0)))
        r = diameter / 2.0
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", self.params.get("y", 0.0)))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["diameter"] = diameter
        self.params["height"] = diameter
        self.params["z_offset"] = y_offset

        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        doc2d.ksLineSeg(cx - r, cz, cx + r, cz, 3)
        doc2d.ksLineSeg(cx - r, cz, cx + r, cz, 1)
        doc2d.ksArcBy3Points(cx - r, cz, cx, cz + r, cx + r, cz, 1)
        sketch_def.EndEdit()

        rot_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossRotated))
        raw_def = rot_ent.GetDefinition()
        rot_def = self.m5.ksBossRotatedDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksBossRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        rot_def.directionType = self.const.dtNormal
        rot_def.SetSideParam(True, 360.0)
        rot_def.SetSketch(sketch_ent)
        rot_ent.name = f"Шар_{self.feature_id}"
        rot_ent.Create()

        self.operation_entity = rot_ent
        self.part.Update()
        self.part.RebuildModel()
        return True, f"Построен шар Ø{diameter} мм"