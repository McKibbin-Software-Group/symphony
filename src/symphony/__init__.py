from dataclasses import dataclass
from importlib import resources
from typing import Any
from lark import Lark, Tree
from pathlib import Path

@dataclass(frozen=True)
class SourcePosition:
    """
    Position information associated with Symphony declarations.
    
    ### Properties
    - `file_path`: Abosolute path to the source file.
    - `line`: 1-based line number.
    - `column`: 1-based column number.
    """
    file_path: Path
    line: int
    column: int
    
def symphony_parser() -> Lark:
        """
        ### Overview

        Set up and return a Symphony Lark parser.
        
        ### Returns
        
        Configured Lark parser for Symphony.

        ### Exceptions

        Raises an assertion error if the parser cannot be built from the bundled grammar.

        """
        symphony_grammar_file: Path = resources.files("symphony").joinpath("symphony.lark")
        try:
            with resources.as_file(symphony_grammar_file) as grammar_path:
                return Lark.open(
                    grammar_path, 
                    parser="lalr", 
                    propagate_positions=True, 
                    maybe_placeholders=False,
                )
        except Exception as exception:
            assert False, f"Failed to build Symphony parser from bundled Symphony grammar {symphony_grammar_file}: {exception}\n"

class SymphonyTree:

    def __init__(self, parse_tree: Tree, file_path: Path) -> None:

        assert parse_tree is not None, "Parse tree cannot be None"
        assert isinstance(parse_tree, Tree), "parse_tree must be an instance of lark.Tree"
        self.parse_tree: Tree = parse_tree

        assert file_path is not None, "file_path cannot be None"
        assert isinstance(file_path, Path), "file_path must be an instance of pathlib.Path"
        self.file_path: Path = file_path

class SymphonyForest:

    def __init__(self) -> None:
        self._trees: list[SymphonyTree] = []

    @property
    def trees(self) -> list[SymphonyTree]:
        return self._trees
    
    def add(self, tree: SymphonyTree) -> None:
        assert isinstance(tree, SymphonyTree), "tree must be an instance of symphony.SymphonyTree"
        self._trees.append(tree)

