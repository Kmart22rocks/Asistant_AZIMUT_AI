import pythoncom
from features.base_feature import BaseFeature
class EdgeBaseFeature(BaseFeature):
    def __init__(self, feature_id, kompas_connector):
        super().__init__(feature_id, kompas_connector)
        self.extra_operations = []
    def _get_vertex_coords(self, v_raw):
        if not v_raw:
            return None
        try:
            v_def = self.m5.ksVertexDefinition(
                v_raw._oleobj_.QueryInterface(self.m5.ksVertexDefinition.CLSID, pythoncom.IID_IDispatch)
            )
            try:
                pt = v_def.GetPoint(0.0, 0.0, 0.0)
            except Exception:
                pt = v_def.GetPoint()
            if isinstance(pt, tuple):
                if len(pt) >= 4:
                    return (round(float(pt[1]), 3), round(float(pt[2]), 3), round(float(pt[3]), 3))
                if len(pt) == 3:
                    return (round(float(pt[0]), 3), round(float(pt[1]), 3), round(float(pt[2]), 3))
        except Exception:
            pass
        return None
    def _get_edge_key(self, edge_ent, fallback_idx):
        try:
            raw_edef = edge_ent.GetDefinition()
            if raw_edef:
                edef = self.m5.ksEdgeDefinition(
                    raw_edef._oleobj_.QueryInterface(self.m5.ksEdgeDefinition.CLSID, pythoncom.IID_IDispatch)
                )
                c1 = self._get_vertex_coords(edef.GetVertex(True))
                c2 = self._get_vertex_coords(edef.GetVertex(False))
                if c1 and c2 and c1 != c2:
                    return tuple(sorted([c1, c2]))
        except Exception:
            pass
        return ("edge_idx", fallback_idx)
    def _collect_target_edges(self):
        self.sync_refs()
        selected = self._get_selected_entities()
        edges = []
        seen = set()
        idx_counter = 0
        for ent in selected:
            if ent.type == self.const.o3d_edge:
                edges.append(ent)
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
                                e_ent = self._wrap_entity(ecol.GetByIndex(i))
                                if e_ent is not None:
                                    idx_counter += 1
                                    key = self._get_edge_key(e_ent, idx_counter)
                                    if key not in seen:
                                        seen.add(key)
                                        edges.append(e_ent)
                except Exception:
                    pass
        if not edges:
            raw_all = self.part.EntityCollection(self.const.o3d_edge)
            if raw_all:
                all_col = self.m5.ksEntityCollection(
                    raw_all._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
                )
                for i in range(all_col.GetCount()):
                    e_ent = self._wrap_entity(all_col.GetByIndex(i))
                    if e_ent is not None:
                        edges.append(e_ent)
        return edges
    def delete(self):
        self.sync_refs()
        for op in reversed(self.extra_operations):
            if op is not None:
                try:
                    if self.doc3d:
                        self.doc3d.DeleteObject(op)
                except Exception:
                    pass
                try:
                    op.Delete()
                except Exception:
                    pass
        self.extra_operations.clear()
        return super().delete()
class ChamferFeature(EdgeBaseFeature):
    def _create_chamfer_op(self, edge_list, dist1, dist2, op_name, tangent=False):
        chamfer_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_chamfer))
        raw_def = chamfer_ent.GetDefinition()
        chamfer_def = self.m5.ksChamferDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksChamferDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        chamfer_def.tangent = tangent
        chamfer_def.SetChamferParam(True, dist1, dist2)
        raw_arr = chamfer_def.array()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )
        for edge in edge_list:
            arr.Add(edge)
        chamfer_ent.name = op_name
        ok = bool(chamfer_ent.Create()) and bool(chamfer_ent.IsCreated())
        if not ok:
            try:
                chamfer_ent.Delete()
            except Exception:
                pass
            return None
        return chamfer_ent
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        raw_d = self.params.get("distance", self.params.get("size", self.params.get("c", self.params.get("width", self.params.get("radius", 2.0)))))
        dist1 = abs(float(raw_d))
        dist2 = abs(float(self.params.get("distance2", dist1)))
        target_edges = self._collect_target_edges()
        if not target_edges:
            return False, "Не найдены ребра для построения фаски."
        main_op = self._create_chamfer_op(target_edges, dist1, dist2, f"Фаска_{self.feature_id}", False)
        if main_op is not None:
            self.operation_entity = main_op
            self.part.Update()
            self.part.RebuildModel()
            return True, f"Выполнена фаска {dist1} мм (ребер: {len(target_edges)})"
        created_ops = []
        for idx, edge in enumerate(target_edges):
            op = self._create_chamfer_op([edge], dist1, dist2, f"Фаска_{self.feature_id}_{idx + 1}", False)
            if op is not None:
                created_ops.append(op)
        self.part.Update()
        self.part.RebuildModel()
        if not created_ops:
            return False, f"Не удалось построить фаску {dist1} мм (проверьте допустимый размер фаски)"
        self.operation_entity = created_ops[0]
        self.extra_operations = created_ops[1:]
        return True, f"Выполнена фаска {dist1} мм (ребер: {len(created_ops)})"
class FilletFeature(EdgeBaseFeature):
    def _create_fillet_op(self, edge_list, radius, op_name, tangent=False):
        fillet_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_fillet))
        raw_def = fillet_ent.GetDefinition()
        fillet_def = self.m5.ksFilletDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksFilletDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        fillet_def.radius = radius
        fillet_def.tangent = tangent
        raw_arr = fillet_def.array()
        arr = self.m5.ksEntityCollection(
            raw_arr._oleobj_.QueryInterface(self.m5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
        )
        for edge in edge_list:
            arr.Add(edge)
        fillet_ent.name = op_name
        ok = bool(fillet_ent.Create()) and bool(fillet_ent.IsCreated())
        if not ok:
            try:
                fillet_ent.Delete()
            except Exception:
                pass
            return None
        return fillet_ent
    def build(self, params):
        self.sync_refs()
        self.params.update(params)
        raw_r = self.params.get("radius", self.params.get("r", self.params.get("size", self.params.get("distance", 3.0))))
        radius = abs(float(raw_r))
        target_edges = self._collect_target_edges()
        if not target_edges:
            return False, "Не найдены ребра для скругления."
        main_op = self._create_fillet_op(target_edges, radius, f"Скругление_{self.feature_id}", False)
        if main_op is not None:
            self.operation_entity = main_op
            self.part.Update()
            self.part.RebuildModel()
            return True, f"Выполнено скругление R{radius} мм (ребер: {len(target_edges)})"
        created_ops = []
        for idx, edge in enumerate(target_edges):
            op = self._create_fillet_op([edge], radius, f"Скругление_{self.feature_id}_{idx + 1}", False)
            if op is not None:
                created_ops.append(op)
        self.part.Update()
        self.part.RebuildModel()
        if not created_ops:
            return False, f"Не удалось построить скругление R{radius} мм (проверьте допустимый радиус)"
        self.operation_entity = created_ops[0]
        self.extra_operations = created_ops[1:]
        return True, f"Выполнено скругление R{radius} мм (ребер: {len(created_ops)})"