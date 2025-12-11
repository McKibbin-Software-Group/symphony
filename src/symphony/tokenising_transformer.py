import ast
from pathlib import Path
from lark import Discard, Transformer, Token, v_args
from typing import Any
import logging

from symphony import SourcePosition

@v_args(meta=True)
class TokenisingTransformer(Transformer):
    """
    ### Overview

    Transformer that converts a Lark parse tree into a JSON-serializable token structure.

    This is only used for grammar design analysis and debugging.    
    """

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        assert file_path is not None, "file_path cannot be None"
        assert isinstance(file_path, Path), "file_path must be an instance of pathlib.Path"
        self.file_path = file_path

    @staticmethod
    def _position(file_path: Path, token_or_meta: Any) -> SourcePosition:
        line = getattr(token_or_meta, "line", None)
        column = getattr(token_or_meta, "column", None)
        if line is None or column is None:
            raise AttributeError("Position data not available; ensure positions are propagated in the parser.")
        return SourcePosition(file_path=file_path, line=line, column=column)

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    def token(self, tok: Token) -> Any:
        return {"type": tok.type, "value": str(tok)}

    def __default_token__(self, token: Token) -> Any:
        return {"type": token.type, "value": token.value}

    def __default__(self, data: str, children: list[Any], meta: Any) -> Any:
        def normalise(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, list):
                return [normalise(item) for item in value]
            if isinstance(value, dict):
                return {key: normalise(val) for key, val in value.items()}
            return value

        return {"type": data, "children": [normalise(child) for child in children]}

    ###############################################
    # Handlers for Include declarations
    ###############################################

    def include_declaration(self, meta: Any, children: list[Any]) -> Any:
        """
        ### Overview

        Handle include declarations by resolving the file path and logging the inclusion.

        ### Parameters

        - `meta`: Metadata about the include declaration.
        - `children`: list of length 1 containing:
            - The file path to include as a string.

        """
        position = self._position(file_path=self.file_path, token_or_meta=meta)
        file_path: Path = children[0]
        assert file_path.exists(), f"Included file does not exist: {file_path} (included at {position} in {self.file_path})"
        return self.__default__(data="include_declaration", children=children, meta=meta)

    def INCLUDE(self, token: Token) -> Any:
        """ 
        Discard the INCLUDE token.
        """
        return Discard

    def FILE_PATH(self, token: Token) -> Any:
        """
        Convert the file path token to a Path object (absolute or relative).
        """
        return (self.file_path.parent / Path(ast.literal_eval(token.value))).resolve()

    
