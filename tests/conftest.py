from typing import Tuple
from lark import Tree, UnexpectedInput
import pytest
from pathlib import Path
from symphony import (
    DiagnosticBag,
    SymphonyDiagnosticsException,
    SymphonyFile,
    SymphonyFiles,
    report_diagnostics,
    symphony_parser,
)
from symphony.loader import Loader, LoaderResult


@pytest.fixture
def data_folder() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture
def root_folder() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def results_folder(root_folder: Path) -> Path:
    result: Path = root_folder / "results"
    result.mkdir(exist_ok=True)
    return result


@pytest.fixture
def models_folder(data_folder: Path) -> Path:
    return data_folder / "models"


@pytest.fixture
def categories_file(models_folder: Path) -> Path:
    return models_folder / "categories.sym"


@pytest.fixture
def categories_with_syntax_errors_file(models_folder: Path) -> Path:
    return models_folder / "categories_with_syntax_errors.sym"


@pytest.fixture
def dimensions_file(models_folder: Path) -> Path:
    return models_folder / "dimensions.sym"


@pytest.fixture
def domains_file(models_folder: Path) -> Path:
    return models_folder / "domains.sym"


@pytest.fixture
def variables_file(models_folder: Path) -> Path:
    return models_folder / "variables.sym"


@pytest.fixture
def equations_file(models_folder: Path) -> Path:
    return models_folder / "equations.sym"


def symphony_file_contents(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as exception:
        assert False, f"Failed to read input file {file_path}: {exception}\n"


def symphony_file(file_path: Path) -> SymphonyFile:
    try:
        tree: Tree = symphony_parser().parse(symphony_file_contents(file_path))
    except UnexpectedInput as err:
        assert False, f"Failed to parse Lark Tree from {file_path}\n"
    return SymphonyFile(file_path=file_path, tree=tree)


@pytest.fixture
def categories_symphony_file(categories_file: Path) -> SymphonyFile:
    return symphony_file(categories_file)


@pytest.fixture
def categories_with_syntax_errors_symphony_file(
    categories_with_syntax_errors_file: Path,
) -> SymphonyFile:
    return symphony_file(categories_with_syntax_errors_file)


@pytest.fixture
def dimensions_symphony_file(dimensions_file: Path) -> SymphonyFile:
    return symphony_file(dimensions_file)


@pytest.fixture
def domains_symphony_file(domains_file: Path) -> SymphonyFile:
    return symphony_file(domains_file)


@pytest.fixture
def variables_symphony_file(variables_file: Path) -> SymphonyFile:
    return symphony_file(variables_file)


@pytest.fixture
def equations_symphony_file(equations_file: Path) -> SymphonyFile:
    return symphony_file(equations_file)


def symphony_files(root_file_path: Path) -> LoaderResult:
    """
    Load all discoverable Symphony files starting from the given root file path.
    """
    result: LoaderResult = Loader().load_symphony_files(root_file_path=root_file_path)
    return result


@pytest.fixture
def categories_symphony_files_loader_result(categories_file: Path) -> LoaderResult:
    return symphony_files(categories_file)


@pytest.fixture
def categories_with_syntax_errors_symphony_files_loader_result(
    categories_with_syntax_errors_file: Path,
) -> SymphonyFiles:
    return symphony_files(categories_with_syntax_errors_file)


@pytest.fixture
def dimensions_symphony_files_loader_result(dimensions_file: Path) -> LoaderResult:
    return symphony_files(dimensions_file)


@pytest.fixture
def domains_symphony_files_loader_result(domains_file: Path) -> LoaderResult:
    return symphony_files(domains_file)


@pytest.fixture
def variables_symphony_files_loader_result(variables_file: Path) -> LoaderResult:
    return symphony_files(variables_file)


@pytest.fixture
def equations_symphony_files_loader_result(equations_file: Path) -> LoaderResult:
    return symphony_files(equations_file)
