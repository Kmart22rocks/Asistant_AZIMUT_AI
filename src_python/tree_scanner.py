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

    def get_compact_tree(self, active_features: dict) -> dict:
        return {
            "операции_агента": {
                fid: feat.params for fid, feat in active_features.items()
            },
            "выделено_мышкой": self.get_selected_objects()
        }