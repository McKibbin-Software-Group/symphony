# Processor features

New differences logging system

# Grammar features

No changes

## Examples

Valid example:

```bash
python ToAST.py --grammar grammar.lark model.sym
```

The processor currently fails to pick this next example as being invalid.

Invalid example where the one member is illegally included in two categories of members:

```bash
python ToAST.py --grammar grammar.lark bad1.sym
```