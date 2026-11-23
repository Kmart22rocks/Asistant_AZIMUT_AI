from features.base_feature import BaseFeature


class ChamferFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        dist1 = float(params.get("distance", 2))
        dist2 = float(params.get("distance2", dist1))

        self.operation_entity = self._new_entity(self.OBJ_CHAMFER)
        self.operation_entity.name = f"Фаска {dist1:g}x{dist2:g}"
        chamfer_def = self.m5.ksChamferDefinition(self.operation_entity.GetDefinition())
        chamfer_def.SetChamferParam(True, dist1, dist2)

        edge_array = self.m5.ksEntityCollection(chamfer_def.array())
        selected_edges = self._get_selected_entities(self.OBJ_EDGE)
        selected_faces = self._get_selected_entities(self.OBJ_FACE)

        if selected_edges or selected_faces:
            for e in selected_edges:
                edge_array.Add(e)
            for f in selected_faces:
                edge_array.Add(f)
        else:
            all_edges = self.m5.ksEntityCollection(self.part.EntityCollection(self.OBJ_EDGE))
            for i in range(all_edges.GetCount()):
                edge_array.Add(all_edges.GetByIndex(i))

        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        dist1 = float(self.params.get("distance", 2))
        dist2 = float(self.params.get("distance2", dist1))
        chamfer_def = self.m5.ksChamferDefinition(self.operation_entity.GetDefinition())
        chamfer_def.SetChamferParam(True, dist1, dist2)
        self.operation_entity.name = f"Фаска {dist1:g}x{dist2:g}"
        self.operation_entity.Update()
        self.part.Update()
        return True


class FilletFeature(BaseFeature):
    def build(self, params: dict) -> bool:
        self.params = params
        radius = float(params.get("radius", 2))

        self.operation_entity = self._new_entity(self.OBJ_FILLET)
        self.operation_entity.name = f"Скругление R{radius:g}"
        fillet_def = self.m5.ksFilletDefinition(self.operation_entity.GetDefinition())
        fillet_def.radius = radius
        fillet_def.tangent = True

        edge_array = self.m5.ksEntityCollection(fillet_def.array())
        selected_edges = self._get_selected_entities(self.OBJ_EDGE)
        selected_faces = self._get_selected_entities(self.OBJ_FACE)

        if selected_edges or selected_faces:
            for e in selected_edges:
                edge_array.Add(e)
            for f in selected_faces:
                edge_array.Add(f)
        else:
            all_edges = self.m5.ksEntityCollection(self.part.EntityCollection(self.OBJ_EDGE))
            for i in range(all_edges.GetCount()):
                edge_array.Add(all_edges.GetByIndex(i))

        self.operation_entity.Create()
        self.part.Update()
        return True

    def update(self, new_params: dict) -> bool:
        self.params.update(new_params)
        radius = float(self.params.get("radius", 2))
        fillet_def = self.m5.ksFilletDefinition(self.operation_entity.GetDefinition())
        fillet_def.radius = radius
        self.operation_entity.name = f"Скругление R{radius:g}"
        self.operation_entity.Update()
        self.part.Update()
        return True