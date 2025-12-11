from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict, List, Set, Tuple, Iterable, cast

from lark import Lark

from symphony import SymphonyTree
from tests.conftest import parser



@dataclass
class Module:
    file_path: Path
    # Various objects declared in the module.
    # includes: List[IncludeNode]
    # declarations: List[DeclarationNode]


@dataclass
class Model:
    modules: Dict[Path, Module]

class ModelLoader:
    def __init__(self) -> None:

        self.modules_by_path: Dict[Path, Module] = {}

    def declaration(model_file:Path) -> str:
        try:
            return model_file.read_text(encoding="utf-8")
        except OSError as exception:
            assert False, f"Failed to read input file {model_file}: {exception}\n"

    def parse_tree(parser: Lark, model_file: Path) -> SymphonyTree:
        try:
            return SymphonyTree(parser.parse(declaration(model_file)), model_file)
        except UnexpectedInput as err:
            assert False, f"Failed to parse Lark Tree from {model_file}\n"






    def load_model(self, root_file_path: Path) -> Model:
        root_file_path = root_file_path.resolve()
        self._load_recursive(root_file_path, set())

        # Union of declarations from all modules, order independent for semantics
        all_declarations: List[DeclarationNode] = []
        for module in self._modules_in_deterministic_order():
            all_declarations.extend(module.declarations)

        return Model(
            modules=self.modules_by_path,
            declarations=all_declarations,
        )

    def _modules_in_deterministic_order(self) -> Iterable[Module]:
        for file_path in sorted(self.modules_by_path.keys()):
            yield self.modules_by_path[file_path]

    def _load_recursive(
        self,
        file_path: Path,
        visiting: Set[Path],
    ) -> None:
        file_path = file_path.resolve()
        if file_path in self.modules_by_path:
            return
        if file_path in visiting:
            raise RuntimeError(f"Cyclic include detected at {file_path}")
        visiting.add(file_path)

        top_level_nodes: List[TopLevelNode] = parse_module_file(self.parser, file_path)

        includes: List[IncludeNode] = []
        declarations: List[DeclarationNode] = []
        for node in top_level_nodes:
            if isinstance(node, IncludeNode):
                includes.append(node)
            else:
                declarations.append(cast(DeclarationNode, node))

        module = Module(
            file_path=file_path,
            includes=includes,
            declarations=declarations,
        )
        self.modules_by_path[file_path] = module

        # Follow include graph, but we do not splice declarations at the include site
        for include_node in includes:
            target_file_path = (file_path.parent / include_node.target_path).resolve()
            self._load_recursive(target_file_path, visiting)

        visiting.remove(file_path)
