from lark import Discard, Transformer, v_args

@v_args(meta=True)
class BaseTransformer(Transformer):
    """
    ### Overview

    This is the base transformer that we adapt to create tailored Transformers that can 
    handle various Symphony processing passes.
    
    """

    def __init__(self) -> None:
        super().__init__()
