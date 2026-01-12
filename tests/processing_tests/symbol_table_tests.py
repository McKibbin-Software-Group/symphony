import logging
from pathlib import Path
from symphony.abstract_syntax_tree_transformer import ASTLoaderResult
from symphony.symbol_table import SymbolTable


def test_categories_symbol_table_generation(
    categories_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    modules = categories_ast_loader_result.modules
    symbol_table = SymbolTable.build(modules, categories_ast_loader_result.diagnostics)

def test_dimensions_symbol_table_generation(
    dimensions_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    modules = dimensions_ast_loader_result.modules
    symbol_table = SymbolTable.build(modules, dimensions_ast_loader_result.diagnostics)
    symbol_table.diagnostics.report_diagnostics()
    for dimension_name, dimension in symbol_table.dimensions.items():
        logging.info(f"Dimension '{dimension_name}' has members: {dimension.members}")
    
def test_domains_symbol_table_generation(
    domains_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    modules = domains_ast_loader_result.modules
    symbol_table = SymbolTable.build(modules, domains_ast_loader_result.diagnostics)
    if symbol_table is None:
        logging.error("Symbol table generation failed due to previous errors.")
        return
    for dimension_name, dimension in symbol_table.dimensions.items():
        logging.info(f"Dimension '{dimension_name}' has members: {dimension.members}")
    for domain_name, domain in symbol_table.domains.items():
        logging.info(f"Domain '{domain_name}' has tuples: {domain.tuples}")

def test_variables_symbol_table_generation(
    variables_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    modules = variables_ast_loader_result.modules
    symbol_table = SymbolTable.build(modules, variables_ast_loader_result.diagnostics)

def test_equations_symbol_table_generation(
    equations_ast_loader_result: ASTLoaderResult, results_folder: Path
):
    modules = equations_ast_loader_result.modules
    symbol_table = SymbolTable.build(modules, equations_ast_loader_result.diagnostics)
