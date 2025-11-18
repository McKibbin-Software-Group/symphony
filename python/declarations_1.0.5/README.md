# Processor features

No changes

# Grammar features

Improved the grammar documentation.

## Examples

Valid example:

```bash
python ToAST.py --grammar grammar.lark model.sym
```

Invalid example where the one member is illegally included in two categories of members:

```bash
python ToAST.py --grammar grammar.lark bad1.sym
```