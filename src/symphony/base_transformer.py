import ast
import logging
from pathlib import Path
from lark import Discard, Token, Transformer, v_args

from symphony import DiagnosticBag


@v_args(meta=True)
class BaseTransformer(Transformer):
    """
    ### Overview

    This is the base transformer that we adapt to create tailored Transformers that can
    handle various Symphony processing passes.

    """

    def __init__(self, file_path: Path, diagnostics: DiagnosticBag) -> None:
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

        assert diagnostics is not None, "diagnostics cannot be None"
        assert isinstance(
            diagnostics, DiagnosticBag
        ), "diagnostics must be an instance of DiagnosticBag"
        self._diagnostics = diagnostics

    @property
    def file_path(self) -> Path:
        """
        ### Overview

        Get the path of the Symphony file being transformed.

        ### Returns

        - `Path`: The path of the Symphony file.
        """
        return self._file_path

    @property
    def diagnostics(self) -> DiagnosticBag:
        """
        ### Overview

        Get the DiagnosticBag for collecting diagnostics during transformation.

        ### Returns

        - `DiagnosticBag`: The diagnostic bag.
        """
        return self._diagnostics

    def parse_escaped_string(self, token: Token) -> str:
        """
        ### Overview

        Convert an ESCAPED_STRING token into its Python string content.

        ### Arguments

        - `token: Token`: The Lark token representing an escaped string.

        """
        return ast.literal_eval(token.value)

    def triple_string_value(self, token: Token) -> str:
        """
        Convert a TRIPLE_STRING token into its text content.

        The grammar uses a regex token like /\"\"\"(.|\n|\r)*?\"\"\"/.
        """
        
        raw: str = token.value
        if raw.startswith('"""') and raw.endswith('"""') and len(raw) >= 6:
            text: str = raw[3:-3]
        
        # Remove leading and trailing whitespace/newlines
        result: str = text.strip()

        return result
