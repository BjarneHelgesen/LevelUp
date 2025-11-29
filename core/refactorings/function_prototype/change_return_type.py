from typing import Optional
from core.refactorings.base_refactoring import BaseRefactoring
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.repo.git_commit import GitCommit
from .change_function_prototype import ChangeFunctionPrototypeRefactoring
from .prototype_change_spec import PrototypeChangeSpec


class ChangeReturnTypeRefactoring(BaseRefactoring):
    def get_probability_of_success(self) -> float:
        return 0.3

    def apply(self, symbol: FunctionSymbol, new_return_type: str) -> Optional[GitCommit]:
        change_spec = PrototypeChangeSpec()
        change_spec.set_return_type(new_return_type)

        core_refactoring = ChangeFunctionPrototypeRefactoring(self.repo)
        return core_refactoring.apply(symbol, change_spec)
