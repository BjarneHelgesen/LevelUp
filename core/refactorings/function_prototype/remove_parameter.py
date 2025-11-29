from typing import Optional
from core.refactorings.base_refactoring import BaseRefactoring
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.repo.git_commit import GitCommit
from .change_function_prototype import ChangeFunctionPrototypeRefactoring
from .prototype_change_spec import PrototypeChangeSpec


class RemoveParameterRefactoring(BaseRefactoring):
    def get_probability_of_success(self) -> float:
        return 0.15

    def apply(self, symbol: FunctionSymbol, param_index: int) -> Optional[GitCommit]:
        change_spec = PrototypeChangeSpec()
        change_spec.remove_parameter(param_index)

        core_refactoring = ChangeFunctionPrototypeRefactoring(self.repo)
        return core_refactoring.apply(symbol, change_spec)
