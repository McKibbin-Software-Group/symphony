# Python Symphony Processor

## Overview

Parse declarations from a .sym file and print the AST.

Run the `setup_python.py` script before doing anything else. This will set up the Python virtual environment.

Install required Python packages. From the `/workspaces/symphony` directory use the VS Code terminal to run:

```bash
uv pip install -r requirements
```

## Processor usage

usage: symphony_toast.py [-h] [--format {tree,summary}] [--show-pos] grammar input

positional arguments:
  grammar               Path to the .lark grammar file.
  input                 Path to the .sym model file.

options:
  -h, --help            show this help message and exit
  --format {tree,summary}
                        Choose 'tree' for a full AST tree or 'summary' for one line per declaration.
  --show-pos            Include line/column position fields in the output.