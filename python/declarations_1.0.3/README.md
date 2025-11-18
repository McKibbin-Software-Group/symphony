# Grammar features

Added categories (groups of unique members that are mutually exclusive) and dimensions etc.

## Examples

Valid example:

```bash
python ToAST.py --grammar grammar.lark model.sym
```

Failing example where the one member is illegally included in two categories of members:

```bash
python ToAST.py --grammar grammar.lark bad1.sym
```