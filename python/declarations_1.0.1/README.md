# Grammar features

General declarations of named entities that come with a label and optional description.

Added a range of different types of declarations reserving those names in the grammar:

```sym
"value"
"dimension"
"dimensions"
"domain"
"parameter"
"variable"
"equation"
```

## Run example

```bash
python ToAST.py --grammar grammar.lark model.sym
```