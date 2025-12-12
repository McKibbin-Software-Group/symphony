import pytest
from symphony.loader import Loader


@pytest.fixture
def loader() -> Loader:
    return Loader()
