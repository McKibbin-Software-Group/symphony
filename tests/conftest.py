import pytest
from pathlib import Path

@pytest.fixture
def data_folder():
    return Path(__file__).parent / "data"

@pytest.fixture
def models_folder(data_folder: Path):
    return data_folder / "models"

@pytest.fixture
def members_file(models_folder: Path):
    return models_folder / "members.sym"

@pytest.fixture
def categories_file(models_folder: Path):
    return models_folder / "categories.sym"

@pytest.fixture
def dimensions_file(models_folder: Path):
    return models_folder / "dimensions.sym"

