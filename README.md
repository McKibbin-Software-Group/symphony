# Symphony

Python implementation of a model definition language drawing on [SYM](https://github.com/pjwilcoxen/sym).

## Resources

[Wiki Functional specification](https://github.com/McKibbin-Software-Group/symphony/wiki/Symphony-specification)

## Contents

* [Sym examples](sym)
* [Python implementation of Symphony using the Lark parser](python/README.md).

## Python Symphony Processor

### Overview

Parse declarations from a .sym file and print the AST.

Run the `setup_python.py` script before doing anything else. This will set up the Python virtual environment.

Install required Python packages. From the `/workspaces/symphony` directory use the VS Code terminal to run:

```bash
uv pip install -r requirements
```

### Processor usage

#### Processor pass 1

Parse into an abstract syntax tree in pass 1:

```bash
usage: processor.py [-h] [--format {tree,summary}] [--show-pos] input

positional arguments:
  input                 Path to the .sym model file.

options:
  -h, --help            show this help message and exit
  --format {tree,summary}
                        Choose 'tree' for a full AST tree or 'summary' for one line per declaration.
  --show-pos            Include line/column position fields in the output.
  ```

  For example:

  ```bash
  usage: processor.py model.sym
  ```