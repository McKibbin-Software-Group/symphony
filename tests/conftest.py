from lark import UnexpectedInput
import pytest
from pathlib import Path
from symphony import SymphonyTree, symphony_parser


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


def symphony_file_contents(model_file: Path) -> str:
    try:
        return model_file.read_text(encoding="utf-8")
    except OSError as exception:
        assert False, f"Failed to read input file {model_file}: {exception}\n"


def parse_tree(symphony_file: Path) -> SymphonyTree:
    try:
        return SymphonyTree(
            symphony_parser().parse(symphony_file_contents(symphony_file)),
            symphony_file,
        )
    except UnexpectedInput as err:
        assert False, f"Failed to parse Lark Tree from {symphony_file}\n"


@pytest.fixture
def categories_parse_tree(categories_file: Path) -> SymphonyTree:
    return parse_tree(categories_file)


@pytest.fixture
def dimensions_parse_tree(dimensions_file: Path) -> SymphonyTree:
    return parse_tree(dimensions_file)


@pytest.fixture
def domains_parse_tree(domains_file: Path) -> SymphonyTree:
    return parse_tree(domains_file)


@pytest.fixture
def variables_parse_tree(variables_file: Path) -> SymphonyTree:
    return parse_tree(variables_file)


@pytest.fixture
def equations_parse_tree(equations_file: Path) -> SymphonyTree:
    return parse_tree(equations_file)
