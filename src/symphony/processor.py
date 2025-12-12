from __future__ import annotations
import sys
import argparse
from pathlib import Path
from typing import List, Optional
from lark import UnexpectedInput
from symphony import SymphonyTree, symphony_parser
from symphony.abstract_syntax_tree import Model
from symphony.model_depictions import model_to_tree, model_to_summary
from symphony.logging import configure_logging, print_parse_error
from symphony.abstract_syntax_tree_transformer import AbstractSyntaxTreeTransformer


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    ### Overview

    Parse command line arguments.

    ### Arguments

    - `argv: Optional[List[str]]`: List of command line arguments. If `None`, uses `sys.argv`.
    """
    parser = argparse.ArgumentParser(
        description="Parse Symphony declarations using the built-in grammar and print the Pass 1 AST.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the .sym model file.",
    )
    parser.add_argument(
        "--format",
        choices=("tree", "summary"),
        default="summary",
        help="Use 'tree' for full AST, 'summary' for one line per declaration.",
    )
    parser.add_argument(
        "--show-pos",
        action="store_true",
        help="Include line/column position fields in the output.",
    )
    parser.add_argument(
        "--log-level",
        default="DEBUG",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """

    ### Overview

    Main entry point for the Symphony processor command line interface.

    ### Arguments

    - `argv: Optional[List[str]]`: List of command line arguments. If `None`, uses `sys.argv`.
    """
    args = _parse_args(argv)

    configure_logging(args.log_level)

    try:
        text = args.input.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"Failed to read input file {args.input}: {exc}\n")
        return 1

    try:
        symphony_tree: SymphonyTree = symphony_parser().parse(text)
        model: Model = AbstractSyntaxTreeTransformer().transform(symphony_tree)
    except UnexpectedInput as err:
        print_parse_error(err, text, args.input)
        return 1

    if args.format == "tree":
        output: str = model_to_tree(model, show_position=args.show_pos)
    else:
        output: str = model_to_summary(model, show_position=args.show_pos)

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
