import pythoncom


class TreeScanner:
    def __init__(self, connector=None):
        self.connector = connector

    @staticmethod
    def get_selected_info(connector):
        result = {"selected_faces": 0, "selected_edges": 0, "selected_objects": []}
        if not connector or not connector.is_connected or not connector.doc3d_api5:
            return result
        try:
            raw_sel = connector.doc3d_api5.GetSelectionMng()
            if not raw_sel:
                return result
            sel_mng = connector.module5.ksSelectionMng(
                raw_sel._oleobj_.QueryInterface(connector.module5.ksSelectionMng.CLSID, pythoncom.IID_IDispatch)
            )
            count = sel_mng.GetCount()
            for i in range(count):
                raw_obj = sel_mng.GetObjectByIndex(i)
                if not raw_obj:
                    continue
                try:
                    ent = connector.module5.ksEntity(
                        raw_obj._oleobj_.QueryInterface(connector.module5.ksEntity.CLSID, pythoncom.IID_IDispatch)
                    )
                    obj_type = ent.type
                    name = ent.name or f"Объект_{i+1}"
                    if obj_type == 6:
                        result["selected_faces"] += 1
                        result["selected_objects"].append({"type": "face", "name": name})
                    elif obj_type == 7:
                        result["selected_edges"] += 1
                        result["selected_objects"].append({"type": "edge", "name": name})
                    else:
                        result["selected_objects"].append({"type": f"type_{obj_type}", "name": name})
                except Exception:
                    pass
        except Exception:
            pass
        return result

    def get_selection_summary(self):
        return self.get_selected_info(self.connector)

    @staticmethod
    def scan_model_tree(connector):
        ops = []
        if not connector or not connector.is_connected or not connector.part_api5:
            return ops
        try:
            part = connector.part_api5
            target_types = (22, 23, 24, 25, 26, 27, 37)
            for t in target_types:
                raw_col = part.EntityCollection(t)
                if not raw_col:
                    continue
                col = connector.module5.ksEntityCollection(
                    raw_col._oleobj_.QueryInterface(connector.module5.ksEntityCollection.CLSID, pythoncom.IID_IDispatch)
                )
                cnt = col.GetCount()
                for i in range(cnt):
                    raw_ent = col.GetByIndex(i)
                    if not raw_ent:
                        continue
                    ent = connector.module5.ksEntity(
                        raw_ent._oleobj_.QueryInterface(connector.module5.ksEntity.CLSID, pythoncom.IID_IDispatch)
                    )
                    if not ent.IsCreated():
                        continue
                    name = ent.name
                    if name and not name.startswith("Эскиз") and not name.startswith("Плоскость"):
                        ops.append({"name": name, "kompas_type": t})
        except Exception:
            pass
        return ops

    def scan_tree(self):
        return self.scan_model_tree(self.connector)