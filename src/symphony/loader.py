from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict
from lark import UnexpectedInput
from symphony import SymphonyTree, symphony_parser
from symphony.tokenising_transformer import TokenisingTransformer

@dataclass
class Module:
    file_path: Path
    # Various objects declared in the module.
    # includes: List[IncludeNode]
    # declarations: List[DeclarationNode]


@dataclass
class Model:
    modules: Dict[Path, Module]

class Loader:

    def __init__(self) -> None:

        self.parser = symphony_parser()
        self.modules_by_path: Dict[Path, Module] = {}

    def read_symphony_file(self, symphony_file_path: Path) -> str:
        try:
            return symphony_file_path.read_text(encoding="utf-8")
        except OSError as exception:
            assert False, f"Failed to read Symphony file {symphony_file_path}: {exception}\n"

    def parse_tree(self, symphony_file_path: Path) -> SymphonyTree:
        try:
            return SymphonyTree(self.parser.parse(self.read_symphony_file(symphony_file_path)), symphony_file_path)
        except UnexpectedInput as err:
            assert False, f"Failed to parse Lark Tree from {symphony_file_path}\n"

    def load_model(self, root_file_path: Path) -> Model:
        root_file_path = root_file_path.resolve()
        self._load_recursive(root_file_path)

        return Model(
            modules=self.modules_by_path,
        )

    def _load_recursive(
        self,
        file_path: Path,
    ) -> None:
        file_path = file_path.resolve()
        if file_path in self.modules_by_path:
            return

        logging.info(f"Loading Symphony file: {file_path}")

        symphony_tree: SymphonyTree = self.parse_tree(symphony_file_path=file_path)
        transformer: TokenisingTransformer = TokenisingTransformer(file_path=file_path)
        transformer.transform(symphony_tree.parse_tree)
        module = Module(
            file_path=file_path,
        )
        self.modules_by_path[file_path] = module
        for included_file in transformer.included_files:
            if not included_file in self.modules_by_path:
                self._load_recursive(included_file)
