import ast
from pathlib import Path
from lark import Discard, Token, Transformer, v_args


@v_args(meta=True)
class BaseTransformer(Transformer):
    """
    ### Overview

    This is the base transformer that we adapt to create tailored Transformers that can
    handle various Symphony processing passes.

    """


    def __init__(self, file_path: Path) -> None:
        """
        ### Overview

        Initialize the JSONTransformer with the path of the Symphony file being transformed.

        ### Arguments

        - `file_path`: Path to the Symphony file being transformed.

        ### Exceptions

        Raises an assertion error if file_path is None or not a Path instance.
        """
        super().__init__()
        assert file_path is not None, "file_path cannot be None"
        assert isinstance(
            file_path, Path
        ), "file_path must be an instance of pathlib.Path"
        self._file_path = file_path

    @property
    def file_path(self) -> Path:
        """
        ### Overview

        Get the path of the Symphony file being transformed.

        ### Returns

        - `Path`: The path of the Symphony file.
        """
        return self._file_path
        
    def parse_escaped_string(self, token: Token) -> str:
        """
        ### Overview
        
        Convert an ESCAPED_STRING token into its Python string content.

        ### Arguments

        - `token: Token`: The Lark token representing an escaped string.

        """
        return ast.literal_eval(token.value)
