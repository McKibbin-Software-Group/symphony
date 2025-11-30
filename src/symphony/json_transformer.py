from lark import Transformer, Token
from typing import Any
import logging

class JSONTransformer(Transformer):
    """
    Transformer to convert a Lark parse tree into a JSON-serializable structure.
    
    Each rule in the grammar is converted into a dictionary with its type and children.
    
    """
    def token(self, tok: Token) -> Any:
        logging.info(tok.type + " " + str(tok))
        return {"type": tok.type, "value": str(tok)}

    def __default_token__(self, tok: Token) -> Any:
        return {"type": tok.type, "value": tok.value}

    def __default__(self, data: str, children: list[Any], meta: Any) -> Any:
        return {"type": data, "children": children}