import ast
from dataclasses import dataclass
import logging
from pathlib import Path
from turtle import position
from typing import Any, Dict, Tuple
from lark import Discard, Token, UnexpectedInput, v_args
from symphony import (
    Diagnostic,
    DiagnosticBag,
    DiagnosticLabel,
    DiagnosticSeverity,
    SymphonyFiles,
    SymphonyFile,
    SourcePosition,
    symphony_position,
    symphony_parser,
    errors,
)
from symphony.base_transformer import BaseTransformer


@dataclass(frozen=True)
class LoaderResult:
    """
    This is the result returned by the loader after loading Symphony files.

    It supports both the loaded Symphony files and any diagnostics encountered.
    """

    symphony_files: SymphonyFiles
    diagnostics: DiagnosticBag


class Loader:

    def __init__(self) -> None:
        """
        ### Overview

        Initialize the Loader for Symphony files, initialising the
        set of symphony files.
        """
        self.parser = symphony_parser()
        self.symphony_files_indexed_by_path: Dict[Path, SymphonyFile] = {}
        self.diagnostics: DiagnosticBag = DiagnosticBag()

    def load_symphony_files(
        self,
        root_file_path: Path,
        *,
        fail_fast: bool = False,
    ) -> LoaderResult:
        """
        ### Overview

        Load a complete Symphony model from the given root file path,
        processing all included files recursively.

        ### Arguments

        - `root_file_path`: Path to the root Symphony file.

        """
        root_file_path = root_file_path.resolve()
        self._load_recursive(file_path=root_file_path, fail_fast=fail_fast)

        if fail_fast:
            self.diagnostics.raise_if_errors()

        return LoaderResult(
            symphony_files=SymphonyFiles(files=self.symphony_files_indexed_by_path),
            diagnostics=self.diagnostics,
        )

    def _load_recursive(
        self,
        *,
        file_path: Path,
        fail_fast: bool = False,
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
        if symphony_file is None:
            if fail_fast:
                self.diagnostics.raise_if_errors()
            return

        transformer: IncludeTransformer = IncludeTransformer(file_path=file_path, diagnostics=self.diagnostics)
        transformer.transform(symphony_file.tree)

        # Store the successfully parsed file even if it had include diagnostics.
        self.symphony_files_indexed_by_path[file_path] = symphony_file

        for included_file in transformer.included_files:
            if not included_file in self.symphony_files_indexed_by_path:
                self._load_recursive(file_path=included_file, fail_fast=fail_fast)

    def parse_symphony_tree_from_file(self, *, file_path: Path) -> SymphonyFile:
        """
        ### Overview

        Parse a Symphony file from the given file path into a SymphonyTree.

        ### Arguments

        - `file_path`: Path to the Symphony file to parse.

        ### Returns

        The SymphonyFile object containing the parse tree, or None if parsing failed.

        """
        source_text = self.read_symphony_file_contents(file_path=file_path)
        if source_text is None:
            return None

        try:
            tree = self.parser.parse(source_text)
            return SymphonyFile(file_path=file_path, tree=tree)
        except UnexpectedInput as exception:
            position = SourcePosition(
                file_path=file_path,
                line=int(getattr(exception, "line", 1) or 1),
                column=int(getattr(exception, "column", 1) or 1),
            )
            expected = getattr(exception, "expected", None)
            expected_text = ""
            if expected:
                expected_text = f" Expected one of: {', '.join(sorted(str(item) for item in expected))}."
            self.diagnostics.add(
                Diagnostic(
                    code=errors.syntax_error,
                    severity=DiagnosticSeverity.error,
                    message=f"Failed to parse file include.{expected_text}",
                    primary_label=DiagnosticLabel(
                        position=position,
                        message="The error occurred near here.",
                        is_primary=True,
                    ),
                    help_text="Check for file path errors in includes near this location.",
                )
            )
            return None

    def read_symphony_file_contents(self, *, file_path: Path) -> str:
        """
        ### Overview

        Read the contents of a Symphony file from the given file path.

        ### Arguments

        - `file_path`: Path to the Symphony file to read.

        ### Returns

        The contents of the Symphony file as a string, or None if reading failed.

        """
        if not file_path.exists():
            self.diagnostics.add(
                Diagnostic(
                    code=errors.missing_file,
                    severity=DiagnosticSeverity.error,
                    message=f"Symphony file does not exist: {file_path}",
                    primary_label=DiagnosticLabel(
                        position=SourcePosition(file_path=file_path, line=1, column=1),
                        message="This file does not exist.",
                        is_primary=True,
                    ),
                    help_text="Check the files that are included in the model.",
                )
            )

        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as exception:
            self.diagnostics.add(
                Diagnostic(
                    code=errors.unreadable_file,
                    severity=DiagnosticSeverity.error,
                    message=f"Symphony file could not be read: {file_path}",
                    primary_label=DiagnosticLabel(
                        position=SourcePosition(file_path=file_path, line=1, column=1),
                        message="This file could not be read.",
                        is_primary=True,
                    ),
                    help_text="Check the permissions for the files that are included in the model.",
                )
            )
            return None


@v_args(meta=True)
class IncludeTransformer(BaseTransformer):
    """
    ### Overview

    Transformer that extracts details about included Symphony files from a Lark parse tree.

    This is used by the Loader to identify and process included files.
    """

    def __init__(self, *, file_path: Path, diagnostics: DiagnosticBag) -> None:
        super().__init__(file_path=file_path)
        self._included_files: set[Path] = set()
        self.diagnostics = diagnostics

    @property
    def included_files(self) -> set[Path]:
        """
        ### Overview

        Set of the files that are included by the Symphony file being transformed.
        """
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

        if len(children) != 1 or not isinstance(children[0], Path):
            self.diagnostics.add(
                Diagnostic(
                    code=errors.include_error,
                    severity=DiagnosticSeverity.error,
                    message="Invalid include declaration.",
                    primary_label=DiagnosticLabel(
                        position=position,
                        message="The include path could not be interpreted as a file path.",
                        is_primary=True,
                    ),
                    help_text='Use: include "relative/or/absolute/path.sym".',
                )
            )
            return self.__default__(
                data="include_declaration", children=children, meta=meta
            )

        file_path: Path = children[0]

        if file_path.exists():
            self.included_files.add(file_path)
        else:
            self.diagnostics.add(
                Diagnostic(
                    code=errors.missing_file,
                    severity=DiagnosticSeverity.error,
                    message="Included Symphony file does not exist.",
                    primary_label=DiagnosticLabel(
                        position=position,
                        message=f'Included Symphony file not found: "{file_path}".',
                        is_primary=True,
                    ),
                    help_text="Check the path is correct, relative to the including file's directory.",
                )
            )

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
