from lark import Transformer, Token
from typing import Any
import logging

class TokenisingTransformer(Transformer):
    """
    ### Overview

    Transformer that converts a Lark parse tree into a JSON-serializable token structure.

    This is only used for grammar design analysis and debugging.    
    """        

    def token(self, tok: Token) -> Any:
        logging.info(tok.type + " " + str(tok))
        return {"type": tok.type, "value": str(tok)}

    def __default_token__(self, tok: Token) -> Any:
        return {"type": tok.type, "value": tok.value}

    def __default__(self, data: str, children: list[Any], meta: Any) -> Any:
        """
        Docstring for __default__
        
        :param self: Description
        :param data: Description
        :type data: str
        :param children: Description
        :type children: list[Any]
        :param meta: Description
        :type meta: Any
        :return: Description
        :rtype: Any

        """
        return {"type": data, "children": children}