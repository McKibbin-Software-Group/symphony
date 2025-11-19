import logging
from pathlib import Path
from symphony_toast import build_parser, parse_decls
from symphony_model import ModelBuilder

logging.basicConfig(level=logging.DEBUG)

grammar_path = Path("grammar.lark")
model_path = Path("model.sym")

parser = build_parser(grammar_path)
text = model_path.read_text(encoding="utf-8")
program = parse_decls(parser, text)

builder = ModelBuilder()
model = builder.build(program)

# Examples:
logging.info(model.symbols.members)
logging.info(model.symbols.categories)
logging.info(model.symbols.dimensions)