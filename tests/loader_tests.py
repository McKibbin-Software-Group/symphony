from pathlib import Path
from symphony.loader import Loader


def test_loader_usage(loader: Loader, equations_file: Path) -> None:
    loader.load_model(root_file_path=equations_file)