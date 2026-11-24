class TreeScanner:
    OBJ_TYPES_RU = {
        1: "Плоскость XY",
        2: "Плоскость ZX",
        3: "Плоскость ZY",
        5: "Эскиз",
        6: "Грань",
        7: "Ребро",
        8: "Вершина",
        14: "Смещенная плоскость",
        22: "Фаска",
        23: "Скругление",
        24: "Выдавливание",
        25: "Вращение",
        26: "Вырез выдавливанием",
        27: "Вырез вращением",
        37: "Отверстие"
    }

    SCAN_TYPES = (22, 23, 24, 25, 26, 27, 37)

    def __init__(self, kompas_connector):
        self.kompas = kompas_connector

    def get_selected_objects(self) -> list:
        if not self.kompas._check_active_doc():
            return []

        selected_list = []
        try:
            m5 = self.kompas.module5
            sel_mng = m5.ksSelectionMng(self.kompas.doc3d_api5.GetSelectionMng())
            count = sel_mng.GetCount()
            for i in range(count):
                ent = m5.ksEntity(sel_mng.GetObjectByIndex(i))
                if ent is not None:
                    t = ent.type
                    selected_list.append({
                        "имя": ent.name if ent.name else self.OBJ_TYPES_RU.get(t, f"Объект_{t}"),
                        "тип": self.OBJ_TYPES_RU.get(t, f"Тип_{t}")
                    })
        except Exception:
            pass
        return selected_list

    def get_native_tree_operations(self) -> list:
        if not self.kompas._check_active_doc():
            return []

        ops = []
        try:
            m5 = self.kompas.module5
            part = m5.ksPart(self.kompas.doc3d_api5.GetPart(-1))
            for t in self.SCAN_TYPES:
                coll = m5.ksEntityCollection(part.EntityCollection(t))
                count = coll.GetCount()
                for i in range(count):
                    ent = m5.ksEntity(coll.GetByIndex(i))
                    if ent is not None and ent.name:
                        ops.append({
                            "имя": ent.name,
                            "тип": self.OBJ_TYPES_RU.get(t, f"Тип_{t}")
                        })
        except Exception:
            pass
        return ops

    def find_native_entity_by_name(self, name_query: str):
        if not self.kompas._check_active_doc() or not name_query:
            return None
        try:
            m5 = self.kompas.module5
            part = m5.ksPart(self.kompas.doc3d_api5.GetPart(-1))
            q = name_query.lower()
            for t in self.SCAN_TYPES:
                coll = m5.ksEntityCollection(part.EntityCollection(t))
                for i in range(coll.GetCount()):
                    ent = m5.ksEntity(coll.GetByIndex(i))
                    if ent is not None and ent.name and q in ent.name.lower():
                        return ent
        except Exception:
            pass
        return None

    def get_compact_tree(self, active_features: dict) -> dict:
        return {
            "операции_агента": {
                fid: feat.params for fid, feat in active_features.items()
            },
            "все_операции_дерева": self.get_native_tree_operations(),
            "выделено_мышкой": self.get_selected_objects()
        }