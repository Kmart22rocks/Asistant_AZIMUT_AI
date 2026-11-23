from abc import ABC, abstractmethod


class BaseFeature(ABC):
    PLANE_XY = 1
    PLANE_XZ = 2
    PLANE_YZ = 3
    DEFAULT_PLANE = PLANE_XZ
    OBJ_SKETCH = 5
    OBJ_FACE = 6
    OBJ_EDGE = 7
    OBJ_PLANE_OFFSET = 14
    OBJ_CHAMFER = 22
    OBJ_FILLET = 23
    OBJ_BOSS_EXTRUDE = 24
    OBJ_BOSS_ROTATE = 25
    OBJ_CUT_EXTRUDE = 26

    def __init__(self, feature_id: str, kompas_connector):
        self.feature_id = feature_id
        self.kompas = kompas_connector
        self.m5 = kompas_connector.module5
        self.doc3d = kompas_connector.doc3d_api5
        self.part = self.m5.ksPart(self.doc3d.GetPart(-1))
        self.sketch_entity = None
        self.operation_entity = None
        self.offset_plane_entity = None
        self.params = {}

    def _new_entity(self, obj_type: int):
        return self.m5.ksEntity(self.part.NewEntity(obj_type))

    def _get_selected_entities(self, target_type: int = 0) -> list:
        result = []
        try:
            sel_mng = self.m5.ksSelectionMng(self.doc3d.GetSelectionMng())
            count = sel_mng.GetCount()
            for i in range(count):
                ent = self.m5.ksEntity(sel_mng.GetObjectByIndex(i))
                if ent is not None:
                    if target_type == 0 or ent.type == target_type:
                        result.append(ent)
        except Exception:
            pass
        return result

    def _get_work_plane(self, z_offset: float = 0.0):
        selected_faces = self._get_selected_entities(self.OBJ_FACE)
        if selected_faces:
            return selected_faces[0]

        base_plane = self.part.GetDefaultEntity(self.DEFAULT_PLANE)
        if abs(z_offset) < 1e-5:
            return base_plane
        if self.offset_plane_entity is None:
            self.offset_plane_entity = self._new_entity(self.OBJ_PLANE_OFFSET)
            self.offset_plane_entity.name = f"Плоскость H={z_offset:g}"
            plane_def = self.m5.ksPlaneOffsetDefinition(self.offset_plane_entity.GetDefinition())
            plane_def.SetPlane(base_plane)
            plane_def.direction = True
            plane_def.offset = z_offset
            self.offset_plane_entity.Create()
        else:
            plane_def = self.m5.ksPlaneOffsetDefinition(self.offset_plane_entity.GetDefinition())
            plane_def.direction = True
            plane_def.offset = z_offset
            self.offset_plane_entity.Update()
        return self.offset_plane_entity

    def delete(self) -> bool:
        if self.operation_entity is not None:
            self.doc3d.ksDeleteEntity(self.operation_entity)
            self.operation_entity = None
        if self.sketch_entity is not None:
            self.doc3d.ksDeleteEntity(self.sketch_entity)
            self.sketch_entity = None
        if self.offset_plane_entity is not None:
            self.doc3d.ksDeleteEntity(self.offset_plane_entity)
            self.offset_plane_entity = None
        self.part.Update()
        return True

    @abstractmethod
    def build(self, params: dict) -> bool:
        pass

    @abstractmethod
    def update(self, new_params: dict) -> bool:
        pass