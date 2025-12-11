from dataclasses import dataclass
from importlib import resources
from typing import Any, Dict
from lark import Lark, Tree
from pathlib import Path

    
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

def symphony_position(file_path: Path, token_or_meta: Any) -> SourcePosition:
    """
    ### Overview

    Extract position information from a Lark token or meta object.
    
    ### Arguments

    - `file_path`: Path to the source file.
    - `token_or_meta`: Lark Token or meta object containing position data.
    
    ### Returns
    
    SourcePosition with file path, line, and column.
    
    ### Exceptions

    Raises an AttributeError if position data is not available. 
    """
    line = getattr(token_or_meta, "line", None)
    column = getattr(token_or_meta, "column", None)
    if line is None or column is None:
        raise AttributeError("Position data not available; ensure line and column positions are propagated in the parser.")
    return SourcePosition(file_path=file_path, line=line, column=column)

class SymphonyTree:

    def __init__(self, parse_tree: Tree, file_path: Path) -> None:

        assert parse_tree is not None, "Parse tree cannot be None"
        assert isinstance(parse_tree, Tree), "parse_tree must be an instance of lark.Tree"
        self.parse_tree: Tree = parse_tree

        assert file_path is not None, "file_path cannot be None"
        assert isinstance(file_path, Path), "file_path must be an instance of pathlib.Path"
        self.file_path: Path = file_path


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

    def to_dictionary(self) -> Dict[str, Any]:
        """
        Convert the SourcePosition to a dictionary representation.
        
        ### Returns
        
        Dictionary with keys 'file_path', 'line', and 'column'.
        """
        return {
            "file_path": str(self.file_path),
            "line": self.line,
            "column": self.column,
        }
    
class SymphonyFile:
    """
    ### Overview
    
    Represents a Symphony module loaded from a file.
    
    ### Properties
    
    - `file_path`: Path to the Symphony file.
    - `symphony_tree`: SymphonyTree representing the parsed content of the file.
    """
    file_path: Path
    symphony_tree: SymphonyTree

class SymphonyFiles:
    """
    ### Overview
    
    Represents a complete Symphony model declaration,
    consisting of multiple modules.
    
    ### Properties
    - `modules`: Mapping from file paths to Module instances.
    
    """
    files: Dict[Path, SymphonyFile]

