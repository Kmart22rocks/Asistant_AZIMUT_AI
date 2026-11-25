import math
from features.base_feature import BaseFeature


class StandardPartFeature(BaseFeature):
    def build(self, params=None):
        if isinstance(params, dict):
            self.params.update(params)
        self.params = {k: v for k, v in self.params.items() if v is not None and v != ""}
        part_type = str(self.params.get("part_type", self.feature_type)).lower()
        gost = str(self.params.get("gost", "")).strip()
        if not gost:
            defaults = {
                "bolt": "7798-70",
                "nut": "5915-70",
                "washer": "11371-78",
                "screw": "11738-84",
                "bearing": "8338-75",
                "pin": "3128-70",
                "key": "23360-78",
            }
            gost = defaults.get(part_type, "7798-70")
        gost_clean = gost.replace("ГОСТ", "").replace("гост", "").strip()

        cx = float(self.params.get("x", 0.0))
        cy = float(self.params.get("z", self.params.get("y", 0.0)))
        base_z = float(self.params.get("y_offset", self.params.get("z_offset", 0.0)))
        dir_sign = -1.0 if float(self.params.get("direction", 1)) < 0 else 1.0

        if part_type in ("bolt", "болт"):
            return self._build_bolt(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("nut", "гайка"):
            return self._build_nut(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("washer", "шайба"):
            return self._build_washer(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("screw", "винт"):
            return self._build_screw(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("bearing", "подшипник"):
            return self._build_bearing(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("pin", "штифт"):
            return self._build_pin(cx, cy, base_z, dir_sign, gost_clean)
        if part_type in ("key", "шпонка"):
            return self._build_key(cx, cy, base_z, dir_sign, gost_clean)
        return self._build_bolt(cx, cy, base_z, dir_sign, gost_clean)

    def _make_sketch(self, name, z_offset):
        plane = self._get_work_plane(z_offset)
        sketch = self.part.NewEntity(self.const.o3d_sketch)
        sketch_def = sketch.GetDefinition()
        sketch_def.SetPlane(plane)
        sketch.name = str(name)
        sketch.Create()
        self.sketch_entity = sketch
        if hasattr(self, "sketches") and isinstance(self.sketches, list):
            self.sketches.append(sketch)
        doc2d = sketch_def.BeginEdit()
        return sketch, sketch_def, doc2d

    def _poly(self, doc2d, cx, cy, r_out, sides=6):
        pts = []
        for i in range(sides):
            a = i * (2.0 * math.pi / sides)
            pts.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a)))
        for i in range(sides):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % sides]
            doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), 1)

    def _rect(self, doc2d, cx, cy, w, h):
        x1, x2 = cx - w / 2.0, cx + w / 2.0
        y1, y2 = cy - h / 2.0, cy + h / 2.0
        doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y1), 1)
        doc2d.ksLineSeg(float(x2), float(y1), float(x2), float(y2), 1)
        doc2d.ksLineSeg(float(x2), float(y2), float(x1), float(y2), 1)
        doc2d.ksLineSeg(float(x1), float(y2), float(x1), float(y1), 1)

    def _oblong(self, doc2d, cx, cy, length, width):
        r = width / 2.0
        straight = max(0.1, length - width)
        dx = straight / 2.0
        doc2d.ksLineSeg(float(cx - dx), float(cy - r), float(cx + dx), float(cy - r), 1)
        doc2d.ksLineSeg(float(cx - dx), float(cy + r), float(cx + dx), float(cy + r), 1)
        doc2d.ksArcByAngle(float(cx + dx), float(cy), float(r), -90.0, 90.0, 1, 1)
        doc2d.ksArcByAngle(float(cx - dx), float(cy), float(r), 90.0, 270.0, 1, 1)

    def _build_bolt(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", self.params.get("diameter", 10.0)))
        length = float(self.params.get("length", self.params.get("height", 40.0)))
        s = d * 1.35 if "7796" in gost else d * 1.5
        k = d * 0.65 if "7796" in gost else d * 0.7
        r_out = (s / math.cos(math.pi / 6.0)) / 2.0

        sk_head, sdef_h, doc2d = self._make_sketch(f"Эскиз головки ГОСТ {gost}", base_z)
        self._poly(doc2d, cx, cy, r_out, 6)
        sdef_h.EndEdit()
        self._extrude_boss(sk_head, k * dir_sign, f"Болт М{int(d)}х{int(length)} ГОСТ {gost}")

        sk_shank, sdef_s, doc2d_s = self._make_sketch(f"Эскиз стержня ГОСТ {gost}", base_z + dir_sign * k)
        doc2d_s.ksCircle(float(cx), float(cy), float(d / 2.0), 1)
        sdef_s.EndEdit()
        res = self._extrude_boss(sk_shank, length * dir_sign, f"Стержень болта ГОСТ {gost}")
        self.part.RebuildModel()
        return res

    def _build_nut(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", self.params.get("diameter", 10.0)))
        s = d * 1.35 if "15521" in gost else d * 1.5
        m = d * 0.5 if "5916" in gost else d * 0.8
        r_out = (s / math.cos(math.pi / 6.0)) / 2.0

        sk, sdef, doc2d = self._make_sketch(f"Эскиз гайки ГОСТ {gost}", base_z)
        self._poly(doc2d, cx, cy, r_out, 6)
        doc2d.ksCircle(float(cx), float(cy), float(d / 2.0), 1)
        sdef.EndEdit()
        res = self._extrude_boss(sk, m * dir_sign, f"Гайка М{int(d)} ГОСТ {gost}")
        self.part.RebuildModel()
        return res

    def _build_washer(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", self.params.get("diameter", 10.0)))
        d_in = d * 1.05
        if "6958" in gost:
            d_out, s = d * 3.0, max(1.0, d * 0.25)
        elif "10450" in gost:
            d_out, s = d * 1.7, max(0.8, d * 0.15)
        else:
            d_out, s = d * 2.0, max(1.0, d * 0.18)

        sk, sdef, doc2d = self._make_sketch(f"Эскиз шайбы ГОСТ {gost}", base_z)
        doc2d.ksCircle(float(cx), float(cy), float(d_out / 2.0), 1)
        doc2d.ksCircle(float(cx), float(cy), float(d_in / 2.0), 1)
        sdef.EndEdit()
        res = self._extrude_boss(sk, s * dir_sign, f"Шайба {int(d)} ГОСТ {gost}")
        self.part.RebuildModel()
        return res

    def _build_screw(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", self.params.get("diameter", 8.0)))
        length = float(self.params.get("length", self.params.get("height", 30.0)))
        dk = d * 1.8 if "17475" in gost else d * 1.5
        k = d * 0.5 if "17475" in gost else (d * 0.7 if "1491" in gost else d * 1.0)

        sk_head, sdef_h, doc2d = self._make_sketch(f"Эскиз головки винта ГОСТ {gost}", base_z)
        doc2d.ksCircle(float(cx), float(cy), float(dk / 2.0), 1)
        sdef_h.EndEdit()
        self._extrude_boss(sk_head, k * dir_sign, f"Винт М{int(d)}х{int(length)} ГОСТ {gost}")

        sk_shank, sdef_s, doc2d_s = self._make_sketch(f"Эскиз стержня винта ГОСТ {gost}", base_z + dir_sign * k)
        doc2d_s.ksCircle(float(cx), float(cy), float(d / 2.0), 1)
        sdef_s.EndEdit()
        res = self._extrude_boss(sk_shank, length * dir_sign, f"Стержень винта ГОСТ {gost}")

        sk_slot, sdef_sl, doc2d_slot = self._make_sketch(f"Эскиз шлица ГОСТ {gost}", base_z)
        if "1491" in gost or "17475" in gost:
            self._rect(doc2d_slot, cx, cy, dk * 0.9, max(1.0, d * 0.2))
        else:
            r_hex = ((d * 0.8) / math.cos(math.pi / 6.0)) / 2.0
            self._poly(doc2d_slot, cx, cy, r_hex, 6)
        sdef_sl.EndEdit()
        self._extrude_cut(sk_slot, k * 0.5, f"Шлиц винта ГОСТ {gost}", reverse=(dir_sign < 0))
        self.part.RebuildModel()
        return res

    def _build_bearing(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", 20.0))
        D = float(self.params.get("D", d * 2.35))
        B = float(self.params.get("B", self.params.get("width", self.params.get("length", (D - d) * 0.5))))
        ring_t = max(2.0, (D - d) * 0.22)

        sk_rings, sdef_r, doc2d = self._make_sketch(f"Эскиз колец ГОСТ {gost}", base_z)
        doc2d.ksCircle(float(cx), float(cy), float(D / 2.0), 1)
        doc2d.ksCircle(float(cx), float(cy), float((D / 2.0) - ring_t), 1)
        doc2d.ksCircle(float(cx), float(cy), float((d / 2.0) + ring_t), 1)
        doc2d.ksCircle(float(cx), float(cy), float(d / 2.0), 1)
        sdef_r.EndEdit()
        res = self._extrude_boss(sk_rings, B * dir_sign, f"Подшипник {int(d)}х{int(D)}х{int(B)} ГОСТ {gost}")

        web_h = B * 0.8 if "7242" in gost else B * 0.5
        sk_mid, sdef_m, doc2d_m = self._make_sketch(f"Эскиз обоймы ГОСТ {gost}", base_z + dir_sign * ((B - web_h) / 2.0))
        doc2d_m.ksCircle(float(cx), float(cy), float((D / 2.0) - ring_t * 0.8), 1)
        doc2d_m.ksCircle(float(cx), float(cy), float((d / 2.0) + ring_t * 0.8), 1)
        sdef_m.EndEdit()
        self._extrude_boss(sk_mid, web_h * dir_sign, f"Сепаратор ГОСТ {gost}")
        self.part.RebuildModel()
        return res

    def _build_pin(self, cx, cy, base_z, dir_sign, gost):
        d = float(self.params.get("d", self.params.get("diameter", 8.0)))
        length = float(self.params.get("length", self.params.get("height", 40.0)))
        draft = 1.15 if "3129" in gost else 0.0

        sk, sdef, doc2d = self._make_sketch(f"Эскиз штифта ГОСТ {gost}", base_z)
        doc2d.ksCircle(float(cx), float(cy), float(d / 2.0), 1)
        sdef.EndEdit()
        res = self._extrude_boss(sk, length * dir_sign, f"Штифт {int(d)}х{int(length)} ГОСТ {gost}", draft, False)
        self.part.RebuildModel()
        return res

    def _build_key(self, cx, cy, base_z, dir_sign, gost):
        b = float(self.params.get("b", self.params.get("width", 8.0)))
        h = float(self.params.get("h", self.params.get("height", 7.0)))
        length = float(self.params.get("length", 40.0))

        sk, sdef, doc2d = self._make_sketch(f"Эскиз шпонки ГОСТ {gost}", base_z)
        if "исп. 2" in gost.lower() or "24071" in gost:
            self._rect(doc2d, cx, cy, length, b)
        else:
            self._oblong(doc2d, cx, cy, length, b)
        sdef.EndEdit()
        res = self._extrude_boss(sk, h * dir_sign, f"Шпонка {int(b)}х{int(h)}х{int(length)} ГОСТ {gost}")
        self.part.RebuildModel()
        return res