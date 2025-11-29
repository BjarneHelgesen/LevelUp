from typing import Optional
from core.refactorings.base_refactoring import BaseRefactoring
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.repo.git_commit import GitCommit
from .change_function_prototype import ChangeFunctionPrototypeRefactoring
from .prototype_change_spec import PrototypeChangeSpec


class RenameParameterRefactoring(BaseRefactoring):
    def get_probability_of_success(self) -> float:
        return 0.85

    def apply(self, symbol: FunctionSymbol, param_index: int, new_name: str) -> Optional[GitCommit]:
        change_spec = PrototypeChangeSpec()
        change_spec.change_parameter_name(param_index, new_name)

        core_refactoring = ChangeFunctionPrototypeRefactoring(self.repo)
        return core_refactoring.apply(symbol, change_spec)
