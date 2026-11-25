import pythoncom
class BaseFeature:
    PLANE_XY = 1
    PLANE_XZ = 2
    PLANE_YZ = 3
    DEFAULT_PLANE = PLANE_XZ
    def __init__(self, feature_id, kompas_connector):
        self.id = feature_id
        self.feature_id = feature_id
        self.feature_type = ""
        self.connector = kompas_connector
        self.params = {}
        self.operation_entity = None
        self.sketch_entity = None
        self.plane_entity = None
        self.used_selected_face = False
        self.sync_refs()
    @property
    def extrusion_entity(self):
        return self.operation_entity
    @extrusion_entity.setter
    def extrusion_entity(self, val):
        self.operation_entity = val
    def sync_refs(self, doc5=None, part5=None):
        self.api5 = self.connector.api5
        self.m5 = self.connector.module5
        self.m7 = self.connector.module7
        self.const = self.connector.const
        self.doc3d = doc5 if doc5 is not None else self.connector.doc3d_api5
        self.part = part5 if part5 is not None else self.connector.part_api5
    def _wrap_entity(self, raw_obj):
        if raw_obj is None:
            return None
        try:
            ole = getattr(raw_obj, "_oleobj_", None)
            if ole is None and hasattr(raw_obj, "_dispobj_"):
                ole = raw_obj._dispobj_._oleobj_
            return self.m5.ksEntity(ole.QueryInterface(self.m5.ksEntity.CLSID, pythoncom.IID_IDispatch))
        except Exception:
            return None
    def _get_selected_entities(self, target_type=None):
        self.sync_refs()
        entities = []
        if not self.doc3d:
            return entities
        try:
            raw_sel = self.doc3d.GetSelectionMng()
            if not raw_sel:
                return entities
            sel_mng = self.m5.ksSelectionMng(
                raw_sel._oleobj_.QueryInterface(self.m5.ksSelectionMng.CLSID, pythoncom.IID_IDispatch)
            )
            count = sel_mng.GetCount()
            for i in range(count):
                ent = self._wrap_entity(sel_mng.GetObjectByIndex(i))
                if ent is not None:
                    if target_type is None or ent.type == target_type:
                        entities.append(ent)
        except Exception:
            pass
        return entities
    def _get_work_plane(self, z_offset=0.0):
        self.sync_refs()
        selected_faces = self._get_selected_entities(target_type=self.const.o3d_face)
        if selected_faces:
            self.used_selected_face = True
            return selected_faces[0]
        self.used_selected_face = False
        base_plane = self._wrap_entity(self.part.GetDefaultEntity(self.DEFAULT_PLANE))
        offset_val = float(z_offset)
        if abs(offset_val) < 1e-5:
            return base_plane
        plane_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_planeOffset))
        raw_def = plane_ent.GetDefinition()
        plane_def = self.m5.ksPlaneOffsetDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksPlaneOffsetDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        plane_def.direction = True if offset_val > 0 else False
        plane_def.offset = abs(offset_val)
        plane_def.SetPlane(base_plane)
        plane_ent.name = f"Плоскость_{self.feature_id}"
        plane_ent.hidden = True
        plane_ent.Create()
        self.plane_entity = plane_ent
        return plane_ent
    def _create_sketch(self, plane_entity, sketch_name=None):
        self.sync_refs()
        sketch_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_sketch))
        raw_def = sketch_ent.GetDefinition()
        sketch_def = self.m5.ksSketchDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksSketchDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        sketch_def.SetPlane(plane_entity)
        sketch_ent.name = sketch_name or f"Эскиз_{self.feature_id}"
        sketch_ent.Create()
        self.sketch_entity = sketch_ent
        return sketch_ent, sketch_def
    def _begin_sketch_edit(self, sketch_def):
        raw_doc2d = sketch_def.BeginEdit()
        return self.m5.ksDocument2D(
            raw_doc2d._oleobj_.QueryInterface(self.m5.ksDocument2D.CLSID, pythoncom.IID_IDispatch)
        )
    def _extrude_boss(self, sketch_ent, height, op_name, draft_angle=0.0, draft_outward=False):
        self.sync_refs()
        extr_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_bossExtrusion))
        raw_def = extr_ent.GetDefinition()
        extr_def = self.m5.ksBossExtrusionDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksBossExtrusionDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        h_val = abs(float(height))
        ang_val = float(draft_angle)
        out_val = bool(draft_outward)
        dir_sign = -1 if float(self.params.get("direction", 1)) < 0 or float(height) < 0 else 1
        extr_def.directionType = self.const.dtNormal if dir_sign > 0 else self.const.dtReverse
        extr_def.SetSideParam(True, self.const.etBlind, h_val, ang_val, out_val)
        extr_def.SetSideParam(False, self.const.etBlind, h_val, ang_val, out_val)
        extr_def.SetSketch(sketch_ent)
        extr_ent.name = op_name
        extr_ent.Create()
        self.operation_entity = extr_ent
        self.part.Update()
        self.part.RebuildModel()
        return extr_ent
    def _extrude_cut(self, sketch_ent, depth, through, op_name):
        self.sync_refs()
        cut_ent = self._wrap_entity(self.part.NewEntity(self.const.o3d_cutExtrusion))
        raw_def = cut_ent.GetDefinition()
        cut_def = self.m5.ksCutExtrusionDefinition(
            raw_def._oleobj_.QueryInterface(self.m5.ksCutExtrusionDefinition.CLSID, pythoncom.IID_IDispatch)
        )
        cut_def.directionType = self.const.dtBoth
        if through:
            cut_def.SetSideParam(True, self.const.etThroughAll, 0, 0, False)
            cut_def.SetSideParam(False, self.const.etThroughAll, 0, 0, False)
        else:
            d_val = abs(float(depth))
            cut_def.SetSideParam(True, self.const.etBlind, d_val, 0, False)
            cut_def.SetSideParam(False, self.const.etBlind, d_val, 0, False)
        cut_def.SetSketch(sketch_ent)
        cut_ent.name = op_name
        cut_ent.Create()
        self.operation_entity = cut_ent
        self.part.Update()
        self.part.RebuildModel()
        return cut_ent
    def is_alive(self):
        if self.operation_entity is None:
            return False
        try:
            return bool(self.operation_entity.IsCreated())
        except Exception:
            return False
    def delete(self):
        self.sync_refs()
        for ent_attr in ("operation_entity", "sketch_entity", "plane_entity"):
            ent = getattr(self, ent_attr, None)
            if ent is not None:
                try:
                    if self.doc3d:
                        self.doc3d.DeleteObject(ent)
                except Exception:
                    pass
                try:
                    ent.Delete()
                except Exception:
                    pass
                setattr(self, ent_attr, None)
        try:
            if self.part:
                self.part.Update()
                self.part.RebuildModel()
            if self.doc3d:
                self.doc3d.RebuildDocument()
        except Exception:
            pass
        return True
    def update(self, params):
        merged = dict(self.params)
        merged.update(params)
        self.delete()
        return self.build(merged)