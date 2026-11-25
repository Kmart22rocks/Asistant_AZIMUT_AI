from features.base_feature import BaseFeature
class RectTubeFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        width = float(self.params.get("width", self.params.get("w", 60.0)))
        length = float(self.params.get("length", self.params.get("l", width)))
        height = float(self.params.get("height", self.params.get("h", 100.0)))
        wall = float(self.params.get("wall", self.params.get("thickness", 4.0)))
        if wall * 2.0 >= min(width, length):
            wall = min(width, length) * 0.2
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["width"] = width
        self.params["length"] = length
        self.params["height"] = height
        self.params["z_offset"] = y_offset
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for hw, hl in ((width / 2.0, length / 2.0), (width / 2.0 - wall, length / 2.0 - wall)):
            x1, z1, x2, z2 = cx - hw, cz - hl, cx + hw, cz + hl
            doc2d.ksLineSeg(x1, z1, x2, z1, 1)
            doc2d.ksLineSeg(x2, z1, x2, z2, 1)
            doc2d.ksLineSeg(x2, z2, x1, z2, 1)
            doc2d.ksLineSeg(x1, z2, x1, z1, 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, height, f"ПрофТруба_{self.feature_id}")
        return True, f"Построена профильная труба {width}x{length}x{wall} мм, высота {height} мм"
class LProfileFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        w = float(self.params.get("width", 50.0))
        l = float(self.params.get("length", w))
        t = float(self.params.get("wall", self.params.get("thickness", 5.0)))
        h = float(self.params.get("height", 100.0))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = h
        self.params["z_offset"] = y_offset
        hw, hl = w / 2.0, l / 2.0
        pts = [
            (cx - hw, cz - hl),
            (cx + hw, cz - hl),
            (cx + hw, cz - hl + t),
            (cx - hw + t, cz - hl + t),
            (cx - hw + t, cz + hl),
            (cx - hw, cz + hl)
        ]
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, h, f"Уголок_{self.feature_id}")
        return True, f"Построен уголок {w}x{l}x{t} мм, высота {h} мм"
class UProfileFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        w = float(self.params.get("width", 80.0))
        l = float(self.params.get("length", 40.0))
        t = float(self.params.get("wall", self.params.get("thickness", 5.0)))
        h = float(self.params.get("height", 100.0))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = h
        self.params["z_offset"] = y_offset
        hw, hl = w / 2.0, l / 2.0
        pts = [
            (cx - hw, cz - hl),
            (cx + hw, cz - hl),
            (cx + hw, cz + hl),
            (cx + hw - t, cz + hl),
            (cx + hw - t, cz - hl + t),
            (cx - hw + t, cz - hl + t),
            (cx - hw + t, cz + hl),
            (cx - hw, cz + hl)
        ]
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, h, f"Швеллер_{self.feature_id}")
        return True, f"Построен швеллер {w}x{l}x{t} мм, высота {h} мм"
class IBeamFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        w = float(self.params.get("width", 80.0))
        l = float(self.params.get("length", 100.0))
        t = float(self.params.get("wall", self.params.get("thickness", 6.0)))
        h = float(self.params.get("height", 120.0))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = h
        self.params["z_offset"] = y_offset
        hw, hl, ht = w / 2.0, l / 2.0, t / 2.0
        pts = [
            (cx - hw, cz - hl),
            (cx + hw, cz - hl),
            (cx + hw, cz - hl + t),
            (cx + ht, cz - hl + t),
            (cx + ht, cz + hl - t),
            (cx + hw, cz + hl - t),
            (cx + hw, cz + hl),
            (cx - hw, cz + hl),
            (cx - hw, cz + hl - t),
            (cx - ht, cz + hl - t),
            (cx - ht, cz - hl + t),
            (cx - hw, cz - hl + t)
        ]
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, h, f"Двутавр_{self.feature_id}")
        return True, f"Построен двутавр {w}x{l}x{t} мм, высота {h} мм"
class TBeamFeature(BaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        w = float(self.params.get("width", 60.0))
        l = float(self.params.get("length", 60.0))
        t = float(self.params.get("wall", self.params.get("thickness", 6.0)))
        h = float(self.params.get("height", 100.0))
        cx = float(self.params.get("x", 0.0))
        cz = float(self.params.get("z", 0.0))
        y_offset = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        self.params["height"] = h
        self.params["z_offset"] = y_offset
        hw, hl, ht = w / 2.0, l / 2.0, t / 2.0
        pts = [
            (cx - hw, cz - hl),
            (cx + hw, cz - hl),
            (cx + hw, cz - hl + t),
            (cx + ht, cz - hl + t),
            (cx + ht, cz + hl),
            (cx - ht, cz + hl),
            (cx - ht, cz - hl + t),
            (cx - hw, cz - hl + t)
        ]
        plane = self._get_work_plane(y_offset)
        sketch_ent, sketch_def = self._create_sketch(plane)
        doc2d = self._begin_sketch_edit(sketch_def)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            doc2d.ksLineSeg(p1[0], p1[1], p2[0], p2[1], 1)
        sketch_def.EndEdit()
        self._extrude_boss(sketch_ent, h, f"Тавр_{self.feature_id}")
        return True, f"Построен тавр {w}x{l}x{t} мм, высота {h} мм"