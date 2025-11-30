from lark import Lark

def test_parser_instantiation(parser: Lark):
    assert parser is not None

