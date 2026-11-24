import pythoncom
from features.base_feature import BaseFeature


class EdgeBaseFeature(BaseFeature):
    def _get_edge_key(self, edge_ent):
        try:
            raw_edef = edge_ent.GetDefinition()
            if raw_edef:
                edef = self.m5.ksEdgeDefinition(
                    raw_edef._oleobj_.QueryInterface(self.m5.ksEdgeDefinition.CLSID, pythoncom.IID_IDispatch)
                )
                v1_raw = edef.GetVertex(True)
                v2_raw = edef.GetVertex(False)
                if v1_raw and v2_raw:
                    v1 = self.m5.ksVertexDefinition(
                        v1_raw._oleobj_.QueryInterface(self.m5.ksVertexDefinition.CLSID, pythoncom.IID_IDispatch)
                    )
                    v2 = self.m5.ksVertexDefinition(
                        v2_raw._oleobj_.QueryInterface(self.m5.ksVertexDefinition.CLSID, pythoncom.IID_IDispatch)
                    )
                    p1 = v1.GetPoint()
                    p2 = v2.GetPoint()
                    if isinstance(p1, tuple) and isinstance(p2, tuple) and len(p1) >= 4 and len(p2) >= 4:
                        c1 = (round(p1[1], 3), round(p1[2], 3), round(p1[3], 3))
                        c2 = (round(p2[1], 3), round(p2[2], 3), round(p2[3], 3))
                        return tuple(sorted([c1, c2]))
        except Exception:
            pass
        return getattr(edge_ent, "_oleobj_", id(edge_ent))

    def _collect_target_edges(self):
        self.sync_refs()
        selected = self._get_selected_entities()
        edges = []
        seen = set()

        def add_unique_edge(e_ent):
            if e_ent is None:
                return
            key = self._get_edge_key(e_ent)
            if key not in seen:
                seen.add(key)
                edges.append(e_ent)

        for ent in selected:
            if ent.type == self.const.o3d_edge:
                add_unique_edge(ent)
            elif ent.type == self.const.o3d_face:
                try:
                    raw_fdef = ent.GetDefinition()
                    if raw_fdef:
                        fdef = self.m5.ksFaceDefinition(
                            raw_fdef._oleobj_.QueryInterface(self.m5.ksFaceDefinition.CLSID, pythoncom.IID_IDispatch)
                        )
                        raw_ecol = fdef.EdgeCollection()
                        if raw_ecol:
                            ecol = self.m5.ksEntityCollection(
                                raw_ecol._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
                            )
                            for i in range(ecol.GetCount()):
                                add_unique_edge(self._wrap_entity(ecol.GetByIndex(i)))
                except Exception:
                    pass

        if not edges:
            raw_all = self.part.EntityCollection(self.const.o3d_edge)
            if raw_all:
                all_col = self.m5.ksEntityCollection(
                    raw_all._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
                )
                for i in range(all_col.GetCount()):
                    add_unique_edge(self._wrap_entity(all_col.GetByIndex(i)))

        return edges


class ChamferFeature(EdgeBaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        dist1 = float(self.params.get("distance", self.params.get("size", self.params.get("c", 2.0))))
        dist2 = float(self.params.get("distance2", dist1))

        target_edges = self._collect_target_edges()
        if not target_edges:
            return False, "Не найдены ребра для построения фаски."

        chamfer_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_chamfer))
        raw_def = chamfer_ent.GetDefinition()
        chamfer_def = self.m5.ksChamferDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksChamferDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        chamfer_def.tangent = False
        chamfer_def.SetChamferParam(True, dist1, dist2)

        raw_arr = chamfer_def.array()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )
        for edge in target_edges:
            arr.Add(edge)

        chamfer_ent.name = f"Фаска_{self.feature_id}"
        ok = chamfer_ent.Create()
        self.operation_entity = chamfer_ent
        self.part.Update()
        self.part.RebuildModel()
        if not ok:
            return False, f"Не удалось построить фаску {dist1} мм (проверьте допустимый размер фаски)"
        return True, f"Выполнена фаска {dist1} мм (ребер: {len(target_edges)})"


class FilletFeature(EdgeBaseFeature):
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        radius = float(self.params.get("radius", self.params.get("r", 3.0)))

        target_edges = self._collect_target_edges()
        if not target_edges:
            return False, "Не найдены ребра для скругления."

        fillet_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_fillet))
        raw_def = fillet_ent.GetDefinition()
        fillet_def = self.m5.ksFilletDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksFilletDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        fillet_def.radius = radius
        fillet_def.tangent = False

        raw_arr = fillet_def.array()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )
        for edge in target_edges:
            arr.Add(edge)

        fillet_ent.name = f"Скругление_{self.feature_id}"
        ok = fillet_ent.Create()
        self.operation_entity = fillet_ent
        self.part.Update()
        self.part.RebuildModel()
        if not ok:
            return False, f"Не удалось построить скругление R{radius} мм (проверьте допустимый радиус)"
        return True, f"Выполнено скругление R{radius} мм (ребер: {len(target_edges)})"