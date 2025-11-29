from typing import Optional, List, Tuple


class PrototypeChangeSpec:
    def __init__(self):
        self.new_return_type: Optional[str] = None
        self.new_function_name: Optional[str] = None
        self.parameter_changes: List[Tuple[int, Optional[str], Optional[str]]] = []
        self.parameters_to_add: List[Tuple[str, str, int]] = []
        self.parameters_to_remove: List[int] = []
        self.qualifiers_to_add: List[str] = []
        self.qualifiers_to_remove: List[str] = []

    def set_return_type(self, new_return_type: str):
        self.new_return_type = new_return_type
        return self

    def set_function_name(self, new_name: str):
        self.new_function_name = new_name
        return self

    def change_parameter_type(self, param_index: int, new_type: str):
        self.parameter_changes.append((param_index, new_type, None))
        return self

    def change_parameter_name(self, param_index: int, new_name: str):
        self.parameter_changes.append((param_index, None, new_name))
        return self

    def change_parameter(self, param_index: int, new_type: str, new_name: str):
        self.parameter_changes.append((param_index, new_type, new_name))
        return self

    def add_parameter(self, param_type: str, param_name: str, position: int = -1):
        self.parameters_to_add.append((param_type, param_name, position))
        return self

    def remove_parameter(self, param_index: int):
        self.parameters_to_remove.append(param_index)
        return self

    def add_qualifier(self, qualifier: str):
        self.qualifiers_to_add.append(qualifier)
        return self

    def remove_qualifier(self, qualifier: str):
        self.qualifiers_to_remove.append(qualifier)
        return self

    def has_changes(self) -> bool:
        return (self.new_return_type is not None or
                self.new_function_name is not None or
                len(self.parameter_changes) > 0 or
                len(self.parameters_to_add) > 0 or
                len(self.parameters_to_remove) > 0 or
                len(self.qualifiers_to_add) > 0 or
                len(self.qualifiers_to_remove) > 0)
