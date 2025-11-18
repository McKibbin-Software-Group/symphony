# Processor features

No changes

# Grammar features

New rules:

- All members in a dimension must be from the same category.
- All members must be in a category.
- No member can be in more than one category.

## Examples

Valid example:

```bash
python ToAST.py --grammar grammar.lark model.sym
```

Invalid example where the one member is illegally included in two categories of members:

```bash
python ToAST.py --grammar grammar.lark bad1.sym
```

Invalid example where a dimension includes a member that is not in any category.

```bash
python ToAST.py --grammar grammar.lark bad2.sym
```