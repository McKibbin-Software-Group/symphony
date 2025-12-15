from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Iterable, Optional, Sequence
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from importlib import resources
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

    def __str__(self):
        """
        Convert the SourcePosition to a human-readable string.

        ### Returns

        String in the format 'file_path:line:column'.
        """
        return f"{self.file_path} line {self.line} column {self.column}"

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


class DiagnosticSeverity(str, Enum):
    error = "error"
    warning = "warning"
    note = "note"


@dataclass(frozen=True)
class DiagnosticLabel:
    """
    A labelled span (or point) in source code.

    Use:
      - primary label: the main location of the issue
      - secondary labels: related locations (e.g., previous definition)
    """

    position: SourcePosition
    message: str
    is_primary: bool = False


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    primary_label: DiagnosticLabel
    secondary_labels: Sequence[DiagnosticLabel] = field(default_factory=tuple)
    help_text: Optional[str] = None

    def is_error(self) -> bool:
        return self.severity == DiagnosticSeverity.error


@dataclass
class DiagnosticBag:
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def add(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        self.diagnostics.extend(diagnostics)

    def has_errors(self) -> bool:
        return any(diagnostic.is_error() for diagnostic in self.diagnostics)

    def raise_if_errors(self) -> None:
        if self.has_errors():
            raise SymphonyDiagnosticsException(self.diagnostics)


class SymphonyException(Exception):
    """
    Raised only when you choose 'fail-fast'. Prefer collecting diagnostics.
    """

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class SymphonyDiagnosticsException(Exception):
    def __init__(self, diagnostics: Sequence[Diagnostic]) -> None:
        super().__init__("Symphony compilation failed with diagnostics.")
        self.diagnostics = diagnostics


def format_diagnostic(diagnostic: Diagnostic) -> str:
    """
    ### Overview

    Format a Diagnostic object into a human-readable string.

    ### Arguments

    - `diagnostic`: Diagnostic object to format.

    ### Returns

    Formatted string representation of the diagnostic.
    """
    lines: list[str] = []
    lines.append(
        f"{diagnostic.primary_label.position}: {diagnostic.severity.value} {diagnostic.code}: {diagnostic.message}"
    )
    lines.append(f"  -> {diagnostic.primary_label.message}")
    for label in diagnostic.secondary_labels:
        lines.append(f"  = {label.position}: {label.message}")
    if diagnostic.help_text is not None:
        lines.append(f"  help: {diagnostic.help_text}")
    return "\n".join(lines)


def report_diagnostics(diagnostics: Sequence[Diagnostic]) -> None:
    """
    ### Overview

    Report diagnostics to the console in a sorted order.

    ### Arguments

    - `diagnostics`: Sequence of Diagnostic objects to report.
    """

    sorted_diagnostics = sorted(
        diagnostics,
        key=lambda diagnostic: (
            diagnostic.severity.value,
            str(diagnostic.primary_label.position.file_path),
            diagnostic.primary_label.position.line,
            diagnostic.primary_label.position.column,
            diagnostic.code,
        ),
    )
    for diagnostic in sorted_diagnostics:
        print(format_diagnostic(diagnostic))
        print()


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
        assert (
            False
        ), f"Failed to build Symphony parser from bundled Symphony grammar {symphony_grammar_file}: {exception}\n"


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
        raise AttributeError(
            "Position data not available; ensure line and column positions are propagated in the parser."
        )
    return SourcePosition(file_path=file_path, line=line, column=column)


class SymphonyFile:
    """
    ### Overview

    Represents a Symphony module loaded from a file.

    ### Properties

    - `file_path`: Path to the Symphony file.
    - `tree`: Lark Tree representing the parsed content of the file.
    """

    def __init__(self, file_path: Path, tree: Tree) -> None:
        assert file_path is not None, "file_path cannot be None"
        assert isinstance(
            file_path, Path
        ), "file_path must be an instance of pathlib.Path"
        self._file_path: Path = file_path

        assert tree is not None, "tree cannot be None"
        assert isinstance(tree, Tree), "tree must be an instance of Tree"
        self._tree: Tree = tree

    @property
    def file_path(self) -> Path:
        """
        ### Overview

        Get the path to the Symphony file.

        ### Returns

        Path to the Symphony file.
        """
        return self._file_path

    @property
    def tree(self) -> Tree:
        """
        ### Overview

        Get the SymphonyTree representing the parsed content of the file.

        ### Returns

        SymphonyTree of the file.
        """
        return self._tree


class SymphonyFiles:
    """
    ### Overview

    Represents a complete Symphony model declaration,
    consisting of multiple modules.

    ### Properties
    - `modules`: Mapping from file paths to Module instances.

    """

    def __init__(self, files: Dict[Path, SymphonyFile]) -> None:
        assert files is not None, "files cannot be None"
        assert isinstance(
            files, dict
        ), "files must be a dictionary mapping Path to SymphonyFile"
        self._files = files

    @property
    def files(self) -> Dict[Path, SymphonyFile]:
        """
        ### Overview

        Get the dictionary that maps file paths to Symphony files.

        ### Returns

        Dictionary mapping from Path to SymphonyFile.
        """
        return self._files

    @property
    def file_list(self) -> List[SymphonyFile]:
        """
        ### Overview

        Get the list of Symphony files in the model.

        ### Returns

        List of SymphonyFile instances.
        """
        return list(self.files.values())
