import ast
from pathlib import Path
from lark import Discard, Transformer, Token, v_args
from typing import Any
import logging

from symphony import SourcePosition, symphony_position
from symphony.base_transformer import BaseTransformer


@v_args(meta=True)
class JSONTransformer(BaseTransformer):
    """
    ### Overview

    Transformer that converts a Lark parse tree into a JSON-serializable token structure.

    This is a base transformer that we adapt to create Transformers that can
    handle various Symphony processing passes.

    """

    def __default_token__(self, token: Token) -> Any:
        position: SourcePosition = symphony_position(self.file_path, token)
        return {
            "type": token.type,
            "value": token.value,
            "position": position.to_dictionary(),
        }

    def __default__(self, data: str, children: list[Any], meta: Any) -> Any:
        position: SourcePosition = symphony_position(self.file_path, meta)

        def normalise(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, list):
                return [normalise(item) for item in value]
            if isinstance(value, dict):
                return {key: normalise(val) for key, val in value.items()}
            return value

        return {
            "type": data,
            "children": [normalise(child) for child in children],
            "position": position.to_dictionary(),
        }
