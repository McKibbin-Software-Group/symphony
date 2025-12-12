import pytest
from pathlib import Path
from symphony.abstract_syntax_tree import Model
from symphony.abstract_syntax_tree_transformer import load_model


@pytest.fixture
def categories_model(categories_file: Path) -> Model:
    return load_model(categories_file)


@pytest.fixture
def dimensions_model(dimensions_file: Path) -> Model:
    return load_model(dimensions_file)


@pytest.fixture
def domains_model(domains_file: Path) -> Model:
    return load_model(domains_file)


@pytest.fixture
def variables_model(variables_file: Path) -> Model:
    return load_model(variables_file)


@pytest.fixture
def equations_model(equations_file: Path) -> Model:
    return load_model(equations_file)
