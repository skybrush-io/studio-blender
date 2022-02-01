"""Takes a Python script and strips all comments from it."""

import sys
import token

from argparse import ArgumentParser
from contextlib import ExitStack
from pathlib import Path
from tokenize import generate_tokens, COMMENT
from typing import IO


def strip_comments(infp: IO[str], outfp: IO[str]):
    prev_toktype = token.INDENT
    last_lineno = -1
    last_col = 0

    tokgen = generate_tokens(infp.readline)
    for toktype, ttext, (slineno, scol), (elineno, ecol), _ in tokgen:
        if slineno > last_lineno:
            last_col = 0
        if scol > last_col:
            outfp.write(" " * (scol - last_col))

        if toktype == token.STRING and prev_toktype == token.INDENT:
            # Docstring
            pass
        elif toktype == COMMENT:
            # Comment
            pass
        else:
            outfp.write(ttext)

        prev_toktype = toktype
        last_col = ecol
        last_lineno = elineno


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "-o", "--output", metavar="FILE", help="name of the output file", default=None
    )
    parser.add_argument("input", help="name of the input file", nargs="?", default=None)
    options = parser.parse_args()

    with ExitStack() as stack:
        if options.input:
            infp = stack.enter_context(Path(options.input).open())
        else:
            infp = sys.stdin
        if options.output:
            outfp = stack.enter_context(Path(options.output).open("w"))
        else:
            outfp = sys.stdout
        strip_comments(infp, outfp)

    return 0


if __name__ == "__main__":
    sys.exit(main())
