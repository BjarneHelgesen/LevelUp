from typing import Optional
from core.refactorings.refactoring_base import RefactoringBase
from core.doxygen.symbols.function_symbol import FunctionSymbol
from core.git_commit import GitCommit
from .change_function_prototype import ChangeFunctionPrototypeRefactoring
from .prototype_change_spec import PrototypeChangeSpec


class ChangeParameterTypeRefactoring(RefactoringBase):
    def get_probability_of_success(self) -> float:
        return 0.25

    def apply(self, symbol: FunctionSymbol, param_index: int, new_type: str) -> Optional[GitCommit]:
        change_spec = PrototypeChangeSpec()
        change_spec.change_parameter_type(param_index, new_type)

        core_refactoring = ChangeFunctionPrototypeRefactoring(self.repo)
        return core_refactoring.apply(symbol, change_spec)
