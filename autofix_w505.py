#!/usr/bin/env python3
"""
autofix_w505: Fix flake8 W505 errors by wrapping long lines in docstrings
and block comments.

This tool searches Python source files for lines longer than max-doc-length
appearing in docstrings or block comments and rewraps them to fit.

Usage: autofix_w505.py [--max-doc-length LEN] [--force-triple-quotes] PATHS...
PATHS can be any mix of individual files and directories. Directories
are searched recursively for *.py files, respecting gitignore rules.
(Run with --help to see additional options.)
"""
# Copyright © 2025 Mike Edmunds. Released under the MIT License.

import argparse
import ast
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterator, Sequence


# Matches bullet or numbered list item marker, including trailing space.
# Bullets: "*" or "-".
# Numbers: one or two digits or one letter, followed by "." or ")".
# (This can be used standalone or as a fragment in a larger regexp.)
re_list_marker = r"(?:[*-]|[1-9][0-9]?[.)]|[A-Za-z][.)])\s+"

re_noqa = re.compile(r"#\s*noqa", re.IGNORECASE)

re_quote = "r?(?:\"\"\"|'''|\"|')"


def rewrap_text(lines: list[str], max_length: int, is_docstring: bool) -> bool:
    """
    Wrap long lines in a docstring or block comment to fit within max_length.

    Args:
        lines: The source lines (including all indents, quotes, and "#" chars);
            modified in place to wrap long lines
        max_length: Maximum line length
        is_docstring: Whether the lines come from a docstring (True) or block
            comment (False); affects recognition of indentation and paragraphs

    Returns:
        Whether lines were modified
    """
    modified = False

    lineno = 0
    while lineno < len(lines):
        if len(lines[lineno]) <= max_length or re_noqa.search(lines[lineno]):
            lineno += 1
            continue

        # This line needs wrapping. Collect the remainder of its "paragraph."
        re_indent = r"\s*" if is_docstring else r"\s*#\s*"
        match = re.match(rf"^({re_indent})({re_list_marker})?", lines[lineno])
        assert match
        indent, list_marker = match.groups()
        list_marker = list_marker or ""
        paragraph_prefix = indent + (" " * len(list_marker))
        paragraph_prefix_len = len(paragraph_prefix)

        start_line = lineno
        end_line = lineno + 1
        if not lines[lineno].rstrip().endswith(":"):
            while end_line < len(lines) and lines[end_line].startswith(
                paragraph_prefix
            ):
                line = lines[end_line][paragraph_prefix_len:].rstrip()
                if not line:
                    # Empty line separates paragraphs.
                    break
                if is_docstring and line.strip() in {'"""', "'''"}:
                    # Don't fill triple quotes into preceding paragraph.
                    break
                if re.match(rf"\s|>>>|{re_list_marker}", line):
                    # Change in indentation separates paragraphs.
                    break
                if re_noqa.search(line):
                    # Leave noqa lines alone.
                    break
                if line.endswith(":"):
                    # Include this line in the paragraph, but not the next one.
                    end_line += 1
                    break
                end_line += 1

        paragraph = "\n".join(
            line[paragraph_prefix_len:] for line in lines[start_line:end_line]
        )
        new_lines = textwrap.wrap(
            paragraph,
            width=max_length,
            initial_indent=indent + list_marker,
            subsequent_indent=paragraph_prefix,
            break_long_words=False,  # Preserve long URLs.
            break_on_hyphens=False,  # Don't break URLs with hyphens.
        )
        lines[start_line:end_line] = new_lines
        modified = True
        lineno = start_line + len(new_lines)

    return modified


class DocstringFinder(ast.NodeVisitor):
    """AST visitor that finds all docstring locations in a Python file."""

    # List of [start, end) line number ranges containing docstrings.
    docstring_locs: list[tuple[int, int]]

    def __init__(self, content: str | None = None) -> None:
        self.docstring_locs = []
        if content is not None:
            self.visit(ast.parse(content))

    def visit(self, node):
        # (ast.get_docstring() returns the docstring content;
        # we need the line numbers and enclosing quotes.)
        # These are the all node types that support docstrings.
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body[0] if len(node.body) > 0 else None
            if (
                body
                and isinstance(body, ast.Expr)
                and isinstance(body.value, ast.Constant)
            ):
                if isinstance(body.value.value, str):
                    # AST line numbers are 1-based.
                    # Result ranges are 0-based with closed [start, open end).
                    start = body.lineno - 1
                    end = getattr(body, "end_lineno", body.lineno)
                    self.docstring_locs.append((start, end))
        super().visit(node)


def ensure_docstring_triple_quotes(lines: list[str]) -> bool:
    """
    Ensure that the docstring uses triple-double-quotes.

    Args:
        lines: The docstring source lines (including all indents and quotes);
            modified in place to convert quotes if necessary

    Returns:
        Whether lines were modified
    """
    modified = False
    match = re.match(rf"^(\s*)({re_quote})(.*)$", lines[0])
    if not match:
        raise ValueError(f"Invalid docstring format: {lines[0]!r}")
    indent, quote, content = match.groups()

    if quote not in {'"""', 'r"""'}:
        modified = True
        raw = "r" if quote.startswith("r") else ""
        end_quote = quote.lstrip("r")
        if not lines[-1].rstrip().endswith(end_quote):
            # BUG: A docstring with an end-of-line comment would confuse this.
            raise ValueError(
                f"Invalid docstring format: {quote} doesn't match {lines[-1]!r}"
            )
        lines[0] = f'{indent}{raw}"""{content}'
        lines[-1] = lines[-1].rstrip()[: -len(end_quote)] + '"""'

    return modified


def process_docstring(
    lines: list[str],
    max_length: int,
    force_triple_quotes: bool,
) -> bool:
    """
    Rewrap the docstring lines if required and update quotes if requested.

    Args:
        lines: The docstring source lines (including all indents and quotes);
            modified in place
        max_length: Maximum line length
        force_triple_quotes: Whether to convert the docstring to
            triple-double-quotes (even a single-quote docstring that fits)

    Returns:
        Whether lines were modified
    """
    modified = False
    if force_triple_quotes or len(lines[0]) > max_length:
        if ensure_docstring_triple_quotes(lines):
            modified = True

    match = re.match(rf"^\s*({re_quote})", lines[0])
    if not match:
        raise ValueError(f"Invalid docstring format: {lines[0]!r}")
    quote = match.group(1)

    # Special case: if a single line docstring doesn't fit, split its quotes
    # to separate lines first. (For multiline docstrings, quotes stay put.)
    if len(lines) == 1 and len(lines[0]) > max_length:
        end_quote = quote[1:] if quote.startswith("r") else quote
        assert end_quote == '"""'  # Due to ensure_docstring_triple_quotes above.
        match = re.match(rf"^(\s*){quote}(.*){end_quote}\s*$", lines[0])
        assert match
        indent, content = match.groups()
        lines[0:1] = [
            f"{indent}{quote}",
            f"{indent}{content}",
            f"{indent}{end_quote}",
        ]
        modified = True

    if any(len(line) > max_length for line in lines):
        if rewrap_text(lines, max_length, is_docstring=True):
            modified = True

    return modified


def process_content(
    content: str,
    max_length: int,
    force_triple_quotes: bool,
    wrap_comments: bool,
    wrap_docstrings: bool,
) -> tuple[list[str], bool]:
    """
    Process the lines of a Python file, wrapping long lines in docstrings and
    block comments.

    Args:
        content: Source code text
        max_length: Maximum line length for docstrings and comments
        force_triple_quotes: Whether to convert all docstrings to
            triple-double-quotes (even single-line docstrings that fit)
        wrap_comments: Whether to wrap block comments
        wrap_docstrings: Whether to wrap docstrings

    Returns:
        Tuple containing the processed lines and a boolean indicating if
        modifications were made
    """
    modified = False
    lines = content.splitlines()

    if wrap_docstrings:
        # Process docstrings in reverse order to avoid line number
        # changes caused by rewrapping.
        parser = DocstringFinder(content)
        docstring_locs = sorted(parser.docstring_locs, reverse=True)
        for start_line, end_line in docstring_locs:
            docstring_lines = lines[start_line:end_line]
            if process_docstring(docstring_lines, max_length, force_triple_quotes):
                lines[start_line:end_line] = docstring_lines
                modified = True

    if wrap_comments:
        lineno = 0
        while lineno < len(lines):
            # Skip shebang lines.
            if lineno == 0 and lines[lineno].startswith("#!"):
                lineno += 1
                continue

            if lines[lineno].lstrip().startswith("#"):
                # Collect all consecutive comment lines.
                start_line = lineno
                lineno = lineno + 1
                while lineno < len(lines) and lines[lineno].lstrip().startswith("#"):
                    lineno += 1
                end_line = lineno
                comment_lines = lines[start_line:end_line]

                if any(len(line) > max_length for line in comment_lines):
                    if rewrap_text(comment_lines, max_length, is_docstring=False):
                        lines[start_line:end_line] = comment_lines
                        modified = True
                lineno = end_line
            else:
                lineno += 1

    return lines, modified


def process_file(
    file_path: Path,
    max_length: int,
    force_triple_quotes: bool,
    wrap_comments: bool,
    wrap_docstrings: bool,
) -> bool:
    """
    Process a single Python file, wrapping long lines in docstrings and block
    comments.

    Args:
        file_path: Path to the Python file
        max_length: Maximum line length for docstrings and comments
        force_triple_quotes: Whether to convert all docstrings to
            triple-double-quotes (even single-line docstrings that fit)
        wrap_comments: Whether to wrap block comments
        wrap_docstrings: Whether to wrap docstrings

    Returns:
        True if the file was modified, False otherwise
    """
    content = file_path.read_text()
    processed_lines, modified = process_content(
        content, max_length, force_triple_quotes, wrap_comments, wrap_docstrings
    )
    if modified:
        file_path.write_text("\n".join(processed_lines) + "\n")
    return modified


def recursive_glob(
    root: Path, glob: str, omit_gitignore: bool = True
) -> Iterator[Path]:
    """
    Recursively find all files matching glob under a root directory.

    Args:
        root: Root directory
        glob: Glob pattern (no need to include leading "**/")
        omit_gitignore: Whether to omit files that git would ignore

    Yields:
        the Path to each matched file
    """
    matches = root.rglob(glob)

    if not omit_gitignore:
        yield from matches
        return

    # For performance, start a single `git check-ignore` process
    # to use for checking all matching paths.
    try:
        process = subprocess.Popen(
            ["git", "check-ignore", "--verbose", "--non-matching", "--stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=root,
            env={**os.environ, "GIT_FLUSH": "true"},
        )
    except (FileNotFoundError, OSError) as error:
        raise RuntimeError(f"Unable to run git check-ignore: {error}") from error

    try:
        for path in matches:
            process.stdin.write(f"{path}\n")
            process.stdin.flush()
            response = process.stdout.readline()
            if response:
                # The output is in the form "ignorefile:lineno:pattern\tpath".
                # The first three fields are empty when path is not ignored.
                if response.startswith("::\t"):
                    yield path
            else:
                # Process exited unexpectedly.
                return_code = process.poll()
                if return_code is not None and return_code != 0:
                    stderr = process.stderr.read() if process.stderr else ""
                    raise RuntimeError(
                        f"git check-ignore exited with code {return_code}:"
                        f" {stderr.strip()}"
                    )
                else:
                    raise RuntimeError("git check-ignore exited unexpectedly")
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


#
# CLI
#

parser = argparse.ArgumentParser(
    description=(
        "Fix flake8 W505 errors by wrapping long lines"
        " in docstrings and block comments."
    )
)
parser.add_argument(
    "paths",
    nargs="+",
    type=Path,
    metavar="PATH",
    help="files or directories (searched recursively for *.py files) to process",
)
parser.add_argument(
    "--max-doc-length",
    type=int,
    metavar="LEN",
    default=79,
    help="maximum length of docstring and block comment lines (default: %(default)s)",
)
parser.add_argument(
    "--force-triple-quotes",
    action="store_true",
    help='convert all docstrings to """ triple-double-quotes',
)
parser.add_argument(
    "--skip-comments", action="store_true", help="don't autofix comments"
)
parser.add_argument(
    "--skip-docstrings", action="store_true", help="don't autofix docstrings"
)
parser.add_argument(
    "--no-gitignore",
    action="store_true",
    help="search directories for all *.py files, even those ignored by git",
)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Main entry point for the autofix_w505 script.

    Args:
        argv: Command-line arguments (sys.argv by default)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    args = parser.parse_args(argv)
    paths = args.paths
    max_length = args.max_doc_length
    force_triple_quotes = args.force_triple_quotes
    omit_gitignore = not args.no_gitignore
    wrap_comments = not args.skip_docstrings
    wrap_docstrings = not args.skip_comments

    processed_count = 0
    modified_count = 0
    error_count = 0
    for path in paths:
        if path.is_file():
            # Process a specifically named file, even if not .py or ignored.
            file_paths = [path]
        elif path.is_dir():
            # Recursively find *.py files
            file_paths = recursive_glob(path, "*.py", omit_gitignore=omit_gitignore)
        else:
            print(f"Not a file or directory: {path}", file=sys.stderr)
            error_count += 1
            continue

        for file_path in file_paths:
            processed_count += 1
            try:
                if process_file(
                    file_path,
                    max_length,
                    force_triple_quotes,
                    wrap_comments,
                    wrap_docstrings,
                ):
                    print(f"Modified: {file_path}")
                    modified_count += 1
            except Exception as error:
                print(f"Error processing {file_path}: {error}", file=sys.stderr)
                error_count += 1

    print(
        f"Processed {processed_count} files,"
        f" modified {modified_count} files,"
        f" {error_count} errors."
    )
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
