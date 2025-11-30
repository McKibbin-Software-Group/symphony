from __future__ import annotations

import sys
import argparse
from importlib import resources
from pathlib import Path
from typing import List, Optional

from lark import UnexpectedInput

from symphony.abstract_syntax_tree import (
    Model,
    abstract_syntax_tree_to_text,
    program_to_summary_text,
)
from symphony.logging import configure_logging, print_parse_error
from symphony.raw_abstract_syntax_tree_transformer import build_parser, parse_declarations


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

    grammar_resource = resources.files("symphony").joinpath("symphony.lark")

    try:
        with resources.as_file(grammar_resource) as grammar_path:
            parser = build_parser(grammar_path)
    except Exception as exc:
        sys.stderr.write(f"Failed to build parser from bundled grammar {grammar_resource}: {exc}\n")
        return 1

    try:
        text = args.input.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"Failed to read input file {args.input}: {exc}\n")
        return 1

    try:
        program: Model = parse_declarations(parser, text)
    except UnexpectedInput as err:
        print_parse_error(err, text, args.input)
        return 1

    if args.format == "tree":
        output = abstract_syntax_tree_to_text(program, show_position=args.show_pos)
    else:
        output = program_to_summary_text(program, show_position=args.show_pos)

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
