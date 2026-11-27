import math
import pythoncom
from features.base_feature import BaseFeature


class ShellFeature(BaseFeature):
    def _get_face_center(self, f_ent):
        try:
            raw_fdef = f_ent.GetDefinition()
            if not raw_fdef:
                return None
            fdef = self.m5.ksFaceDefinition(
                raw_fdef._oleobj_.QueryInterface(self.m5.ksFaceDefinition.CLSID, pythoncom.IID_IDispatch)
            )
            raw_ecol = fdef.EdgeCollection()
            if not raw_ecol:
                return None
            ecol = self.m5.ksEntityCollection(
                raw_ecol._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
            )
            if ecol.GetCount() == 0:
                return None
            sx, sy, sz = 0.0, 0.0, 0.0
            cnt = 0
            for j in range(ecol.GetCount()):
                e_ent = self._wrap_entity(ecol.GetByIndex(j))
                if not e_ent:
                    continue
                raw_edef = e_ent.GetDefinition()
                if not raw_edef:
                    continue
                edef = self.m5.ksEdgeDefinition(
                    raw_edef._oleobj_.QueryInterface(self.m5.ksEdgeDefinition.CLSID, pythoncom.IID_IDispatch)
                )
                for is_first in (True, False):
                    v_raw = edef.GetVertex(is_first)
                    if v_raw:
                        vdef = self.m5.ksVertexDefinition(
                            v_raw._oleobj_.QueryInterface(self.m5.ksVertexDefinition.CLSID, pythoncom.IID_IDispatch)
                        )
                        pt = vdef.GetPoint()
                        if isinstance(pt, tuple) and len(pt) >= 4:
                            sx += float(pt[1])
                            sy += float(pt[2])
                            sz += float(pt[3])
                            cnt += 1
            if cnt > 0:
                return [sx / cnt, sy / cnt, sz / cnt]
        except Exception:
            pass
        return None

    def _find_faces_by_coords(self, target_coords):
        found = []
        try:
            raw_faces = self.part.EntityCollection(self.const.o3d_face)
            if not raw_faces:
                return found
            fcol = self.m5.ksEntityCollection(
                raw_faces._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
            )
            candidates = []
            for i in range(fcol.GetCount()):
                f_ent = self._wrap_entity(fcol.GetByIndex(i))
                if not f_ent:
                    continue
                c = self._get_face_center(f_ent)
                if c is not None:
                    candidates.append((f_ent, c))
            for tc in target_coords:
                best_f = None
                best_d = 1e9
                for f_ent, c in candidates:
                    d = math.sqrt((c[0] - tc[0]) ** 2 + (c[1] - tc[1]) ** 2 + (c[2] - tc[2]) ** 2)
                    if d < best_d:
                        best_d = d
                        best_f = f_ent
                if best_f is not None and best_d < 25.0:
                    found.append(best_f)
        except Exception:
            pass
        return found

    def _find_top_face(self):
        try:
            raw_faces = self.part.EntityCollection(self.const.o3d_face)
            if not raw_faces:
                return None
            fcol = self.m5.ksEntityCollection(
                raw_faces._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
            )
            best_face = None
            max_y = -1e9
            for i in range(fcol.GetCount()):
                f_ent = self._wrap_entity(fcol.GetByIndex(i))
                if not f_ent:
                    continue
                raw_fdef = f_ent.GetDefinition()
                if not raw_fdef:
                    continue
                fdef = self.m5.ksFaceDefinition(
                    raw_fdef._oleobj_.QueryInterface(self.m5.ksFaceDefinition.CLSID, pythoncom.IID_IDispatch)
                )
                if not fdef.IsPlanar():
                    continue
                c = self._get_face_center(f_ent)
                if c is not None and c[1] > max_y:
                    max_y = c[1]
                    best_face = f_ent
            return best_face
        except Exception:
            return None

    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        thickness = float(self.params.get("thickness", self.params.get("wall", self.params.get("t", 2.0))))
        outward = bool(self.params.get("outward", False))
        self.params["thickness"] = thickness
        self.params["outward"] = outward

        shell_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_shellOperation))
        raw_def = shell_ent.GetDefinition()
        shell_def = self.m5.ksShellDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksShellDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        shell_def.thickness = thickness
        shell_def.thinType = not outward

        raw_arr = shell_def.array()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )

        selected_faces = self._get_selected_entities(target_type=self.const.o3d_face)
        if selected_faces:
            saved_coords = []
            for f in selected_faces:
                arr.Add(f)
                c = self._get_face_center(f)
                if c is not None:
                    saved_coords.append(c)
            if saved_coords:
                self.params["edge_coords"] = saved_coords
        elif "edge_coords" in self.params and self.params["edge_coords"]:
            matched = self._find_faces_by_coords(self.params["edge_coords"])
            if matched:
                for f in matched:
                    arr.Add(f)
            else:
                top_face = self._find_top_face()
                if top_face is not None:
                    arr.Add(top_face)
        else:
            top_face = self._find_top_face()
            if top_face is not None:
                arr.Add(top_face)

        shell_ent.name = f"Оболочка_{self.feature_id}"
        ok = shell_ent.Create()
        self.operation_entity = shell_ent
        self.part.Update()
        self.part.RebuildModel()
        if not ok:
            return False, f"Не удалось создать оболочку толщиной {thickness} мм"
        return True, f"Выполнена оболочка (толщина стенки {thickness} мм)"


class HolesGridFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        diameter = float(self.params.get("diameter", self.params.get("d", 8.0)))
        count_x = max(1, int(self.params.get("count_x", self.params.get("count", 3))))
        count_z = max(1, int(self.params.get("count_z", self.params.get("rows", 1))))
        step_x = float(self.params.get("step_x", self.params.get("step", 20.0)))
        step_z = float(self.params.get("step_z", self.params.get("row_step", step_x)))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", self.params.get("y", 0.0)))
        centered = bool(self.params.get("centered", True))
        through = bool(self.params.get("through", True))
        depth = float(self.params.get("depth", 10.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))

        self.params["x"] = cx
        self.params["z"] = cz
        self.params["y_offset"] = y_offset
        self.params["z_offset"] = y_offset
        self.params["diameter"] = diameter
        self.params["count_x"] = count_x
        self.params["count_z"] = count_z
        self.params["step_x"] = step_x
        self.params["step_z"] = step_z

        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)

        start_x = cx - ((count_x - 1) * step_x / 2.0) if centered else cx
        start_z = cz - ((count_z - 1) * step_z / 2.0) if centered else cz
        r = diameter / 2.0

        total = 0
        for ix in range(count_x):
            for iz in range(count_z):
                px = start_x + ix * step_x
                pz = start_z + iz * step_z
                doc2d.ksCircle(px, pz, r, 1)
                total += 1
        sketch_def.EndEdit()

        self._extrude_cut(sketch_ent, depth, through, f"МассивОтверстий_{self.feature_id}")
        return True, f"Выполнен массив из {total} отверстий d={diameter} мм ({count_x}x{count_z})"


class SteppedShaftFeature(BaseFeature):
    def _get_xy_work_plane(self, z_coord):
        base_plane = self._wrap_entity(self.part.GetDefaultEntity(self.PLANE_XY))
        if abs(z_coord) < 1e-5:
            return base_plane
        plane_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_planeOffset))
        raw_def = plane_ent.GetDefinition()
        plane_def = self.m5.ksPlaneOffsetDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksPlaneOffsetDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        plane_def.SetPlane(base_plane)
        plane_def.offset = float(z_coord)
        plane_def.direction = True
        plane_ent.name = f"ПлоскостьВала_{self.feature_id}"
        plane_ent.hidden = True
        plane_ent.Create()
        self.aux_entities.append(plane_ent)
        return plane_ent

    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        steps = self.params.get("steps", [])
        if not steps:
            d1 = float(self.params.get("diameter1", 40.0))
            h1 = float(self.params.get("height1", 20.0))
            d2 = float(self.params.get("diameter2", 25.0))
            h2 = float(self.params.get("height2", 35.0))
            steps = [{"diameter": d1, "height": h1}, {"diameter": d2, "height": h2}]

        bore_d = float(self.params.get("inner_diameter", self.params.get("bore", 0.0)))
        inner_r = max(0.0, bore_d / 2.0)
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_start = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))

        plane_xy = self._get_xy_work_plane(cz)
        sketch_ent, sketch_def = self._create_sketch(plane_xy, f"ЭскизВала_{self.feature_id}")
        doc2d = self._begin_sketch_edit(sketch_def)

        cur_y = y_start
        prev_r = inner_r
        for st in steps:
            d = float(st.get("diameter", st.get("d", 30.0)))
            h = float(st.get("height", st.get("length", st.get("h", 20.0))))
            r = max(inner_r + 1.0, d / 2.0)
            doc2d.ksLineSeg(cx + prev_r, cur_y, cx + r, cur_y, 1)
            doc2d.ksLineSeg(cx + r, cur_y, cx + r, cur_y + h, 1)
            cur_y += h
            prev_r = r

        total_h = cur_y - y_start
        doc2d.ksLineSeg(cx + prev_r, cur_y, cx + inner_r, cur_y, 1)
        doc2d.ksLineSeg(cx + inner_r, cur_y, cx + inner_r, y_start, 1)
        doc2d.ksLineSeg(cx, y_start, cx, cur_y, 3)
        sketch_def.EndEdit()

        self.params["x"] = cx
        self.params["z"] = cz
        self.params["height"] = total_h
        self.params["y_offset"] = y_start
        self.params["z_offset"] = y_start
        self.params["steps"] = steps

        rot_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossRotated))
        raw_def = rot_ent.GetDefinition()
        rot_def = self.m5.ksBossRotatedDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksBossRotatedDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        rot_def.directionType = self.const.dtNormal
        rot_def.SetSideParam(True, 360.0)
        rot_def.SetSketch(sketch_ent)
        rot_ent.name = f"СтупенчатыйВал_{self.feature_id}"
        ok = rot_ent.Create()
        self.operation_entity = rot_ent
        self.part.Update()
        self.part.RebuildModel()
        if not ok:
            return False, "Не удалось построить ступенчатый вал"
        return True, f"Построен ступенчатый вал ({len(steps)} ступеней, общая высота {total_h} мм)"


class AppearanceFeature(BaseFeature):
    COLOR_MAP = {
        "red": (40, 40, 220),
        "красный": (40, 40, 220),
        "blue": (210, 90, 30),
        "синий": (210, 90, 30),
        "green": (60, 170, 50),
        "зеленый": (60, 170, 50),
        "зелёный": (60, 170, 50),
        "yellow": (30, 210, 240),
        "желтый": (30, 210, 240),
        "жёлтый": (30, 210, 240),
        "orange": (20, 130, 240),
        "оранжевый": (20, 130, 240),
        "white": (240, 240, 240),
        "белый": (240, 240, 240),
        "black": (35, 35, 35),
        "черный": (35, 35, 35),
        "чёрный": (35, 35, 35),
        "gray": (140, 140, 140),
        "серый": (140, 140, 140),
        "steel": (175, 170, 165),
        "сталь": (175, 170, 165),
        "стальной": (175, 170, 165),
        "aluminum": (215, 210, 205),
        "алюминий": (215, 210, 205),
        "copper": (80, 115, 185),
        "медь": (80, 115, 185),
        "медный": (80, 115, 185),
        "gold": (55, 175, 212),
        "золото": (55, 175, 212),
        "золотой": (55, 175, 212),
        "brass": (65, 165, 185),
        "латунь": (65, 165, 185),
        "titanium": (150, 145, 140),
        "титан": (150, 145, 140)
    }

    MATERIALS = {
        "сталь": ("Сталь 45 ГОСТ 1050-2013", 7.85),
        "steel": ("Сталь 45 ГОСТ 1050-2013", 7.85),
        "алюминий": ("Д16 ГОСТ 4784-2019", 2.78),
        "aluminum": ("Д16 ГОСТ 4784-2019", 2.78),
        "медь": ("М1 ГОСТ 859-2014", 8.94),
        "copper": ("М1 ГОСТ 859-2014", 8.94),
        "латунь": ("Л63 ГОСТ 15527-2004", 8.44),
        "brass": ("Л63 ГОСТ 15527-2004", 8.44),
        "титан": ("ВТ6 ГОСТ 19807-91", 4.43),
        "titanium": ("ВТ6 ГОСТ 19807-91", 4.43),
        "золото": ("Золото Зл 999,9", 19.32),
        "gold": ("Золото Зл 999,9", 19.32),
        "пластик": ("АБС-пластик", 1.05)
    }

    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        color_key = str(self.params.get("color", self.params.get("material", "steel"))).strip().lower()
        mat_key = str(self.params.get("material", color_key)).strip().lower()

        b, g, r = self.COLOR_MAP.get(color_key, (175, 170, 165))
        if color_key.startswith("#") and len(color_key) == 7:
            try:
                r = int(color_key[1:3], 16)
                g = int(color_key[3:5], 16)
                b = int(color_key[5:7], 16)
            except Exception:
                pass

        color_val = (b << 16) | (g << 8) | r
        try:
            self.part.SetAdvancedColor(color_val, 0.5, 0.6, 0.8, 0.6, 1.0, 0.0)
        except Exception:
            pass

        mat_info = None
        for k, val in self.MATERIALS.items():
            if k in mat_key:
                mat_info = val
                break

        if mat_info:
            try:
                self.part.SetMaterial(mat_info[0], mat_info[1])
            except Exception:
                pass

        self.part.Update()
        self.part.RebuildModel()
        if self.doc3d:
            self.doc3d.RebuildDocument()

        desc = f"Цвет: {color_key}"
        if mat_info:
            desc += f", Материал: {mat_info[0]}"
        return True, f"Установлены свойства детали ({desc})"

    def is_alive(self):
        return True

    def delete(self):
        self.sync_refs()
        try:
            default_col = (175 << 16) | (170 << 8) | 165
            self.part.SetAdvancedColor(default_col, 0.5, 0.6, 0.8, 0.6, 1.0, 0.0)
            self.part.Update()
            self.part.RebuildModel()
        except Exception:
            pass
        return True