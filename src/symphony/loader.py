import ast
import logging
from pathlib import Path
from typing import Any, Dict
from lark import Discard, Token, UnexpectedInput, v_args
from symphony import (
    SymphonyFiles,
    SymphonyFile,
    SourcePosition,
    symphony_position,
    symphony_parser,
)
from symphony.base_transformer import BaseTransformer


class Loader:

    def __init__(self) -> None:
        """
        ### Overview

        Initialize the Loader for Symphony files, initialising the
        set of symphony files.
        """
        self.parser = symphony_parser()
        self.symphony_files_indexed_by_path: Dict[Path, SymphonyFile] = {}

    def load_symphony_files(self, root_file_path: Path) -> SymphonyFiles:
        """
        ### Overview

        Load a complete Symphony model from the given root file path,
        processing all included files recursively.

        ### Arguments

        - `root_file_path`: Path to the root Symphony file.

        """
        root_file_path = root_file_path.resolve()
        self._load_recursive(root_file_path)

        return SymphonyFiles(
            files=self.symphony_files_indexed_by_path,
        )

    def _load_recursive(
        self,
        file_path: Path,
    ) -> None:
        """
        ### Overview

        Recursively load Symphony files starting from the given file path,
        processing all included files.

        ### Arguments

        - `file_path`: Path to the Symphony file to load.

        """
        file_path = file_path.resolve()
        if file_path in self.symphony_files_indexed_by_path:
            return

        logging.info(f"Loading Symphony file: {file_path}")

        symphony_file: SymphonyFile = self.parse_symphony_tree_from_file(
            file_path=file_path
        )
        transformer: IncludeTransformer = IncludeTransformer(file_path=file_path)
        transformer.transform(symphony_file.tree)
        symphony_file: SymphonyFile = SymphonyFile(
            file_path=file_path,
            tree=symphony_file.tree,
        )
        self.symphony_files_indexed_by_path[file_path] = symphony_file
        for included_file in transformer.included_files:
            if not included_file in self.symphony_files_indexed_by_path:
                self._load_recursive(included_file)

    def parse_symphony_tree_from_file(self, file_path: Path) -> SymphonyFile:
        """
        ### Overview

        Parse a Symphony file from the given file path into a SymphonyTree.

        ### Arguments

        - `file_path`: Path to the Symphony file to parse.

        """
        try:
            return SymphonyFile(
                file_path=file_path,
                tree=self.parser.parse(self.read_symphony_file_contents(file_path=file_path)),
            )
        except UnexpectedInput as err:
            assert False, f"Failed to parse Lark Tree from {file_path}\n"

    def read_symphony_file_contents(self, file_path: Path) -> str:
        """
        ### Overview

        Read the contents of a Symphony file from the given file path.

        ### Arguments

        - `file_path`: Path to the Symphony file to read.

        """
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as exception:
            assert False, f"Failed to read Symphony file {file_path}: {exception}\n"


@v_args(meta=True)
class IncludeTransformer(BaseTransformer):
    """
    ### Overview

    Transformer that extracts details about included Symphony files from a Lark parse tree.

    This is used by the Loader to identify and process included files.
    """

    @property
    def included_files(self) -> set[Path]:
        """
        ### Overview

        Set of the files that are included by the Symphony file being transformed.
        """
        if not hasattr(self, "_included_files"):
            self._included_files = set()
        return self._included_files

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

        ### Returns

        The default transformed node for the include declaration.

        ### Exceptions

        Raises an assertion error if the included file does not exist.

        """
        position: SourcePosition = symphony_position(
            file_path=self.file_path, token_or_meta=meta
        )
        file_path: Path = children[0]
        assert (
            file_path.exists()
        ), f"Included file does not exist: {file_path} (See line {position.line} in {self.file_path})"
        self.included_files.add(file_path)
        return self.__default__(
            data="include_declaration", children=children, meta=meta
        )

    def INCLUDE(self, token: Token) -> Any:
        """
        Discard the INCLUDE token.
        """
        return Discard

    def FILE_PATH(self, token: Token) -> Any:
        """
        Convert the file path token to an absolute or relative pathlib.Path object.
        """
        return (self.file_path.parent / Path(ast.literal_eval(token.value))).resolve()
