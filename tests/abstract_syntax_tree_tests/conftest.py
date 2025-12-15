import pytest
from symphony import DiagnosticBag, SymphonyFiles, report_diagnostics
from symphony.abstract_syntax_tree import Modules
from symphony.abstract_syntax_tree_transformer import ASTLoaderResult, load_modules
from symphony.loader import Loader, LoaderResult


@pytest.fixture
def categories_ast_loader_result(categories_symphony_files_loader_result: LoaderResult) -> ASTLoaderResult:
    return load_modules(categories_symphony_files_loader_result)


@pytest.fixture
def categories_with_syntax_errors_ast_loader_result(
    categories_with_syntax_errors_symphony_files_loader_result: LoaderResult,
) -> ASTLoaderResult:
    return load_modules(categories_with_syntax_errors_symphony_files_loader_result)


@pytest.fixture
def dimensions_ast_loader_result(dimensions_symphony_files_loader_result: LoaderResult) -> ASTLoaderResult:
    return load_modules(dimensions_symphony_files_loader_result)


@pytest.fixture
def domains_ast_loader_result(domains_symphony_files_loader_result: LoaderResult) -> ASTLoaderResult:
    return load_modules(domains_symphony_files_loader_result)


@pytest.fixture
def variables_ast_loader_result(variables_symphony_files_loader_result: LoaderResult) -> ASTLoaderResult:
    return load_modules(variables_symphony_files_loader_result)


@pytest.fixture
def equations_ast_loader_result(equations_symphony_files_loader_result: LoaderResult) -> ASTLoaderResult:
    return load_modules(equations_symphony_files_loader_result)
