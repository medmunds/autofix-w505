# autofix_w505

A pure Python command line tool that fixes flake8 W505 "doc-line-too-long" 
errors in Python source files by wrapping long lines in docstrings and block 
comments.

autofix_505 tries to apply minimal fixes to bring docstrings and block comments 
into compliance with flake8's max-doc-length setting, while preserving (the 
intent of) existing formatting when possible.


## Installation

Copy [autofix_w505.py] from this repo to your system.

Tested with Python 3.13. (Probably works back to at least Python 3.9 or so.)

Requires git unless run with the `--no-gitignore` option.


## Usage

```bash
python autofix_w505.py [OPTIONS] PATHS...
```

The PATHS can be one or more files, directories or a mixture. Directories are 
recursively searched for .py files, respecting gitignore by default. (Specific
named files are always processed, even if in gitignore.)

Files are modified in place.

Options:
* `--max-doc-length LEN`: maximum length of docstring and block comment lines 
  (default: 79)
* `--force-triple-quotes`: convert all docstrings to `"""` triple-double-quotes
  (default: leave existing docstring quotes unchangd, except that a single-line 
  docstring that needs wrapping will always be converted to `"""`)
* `--skip-comments`: don't autofix comments
* `--skip-docstrings`: don't autofix docstrings
* `--no-gitignore`: search directories for all *.py files, even those ignored 
  by git (default: when searching directories, skip files ignored by git)

Exit code: 0 for success, 1 if any files are unreadable or unparseable.
(If you just want to find out whether files comply without modifying them,
run flake8 instead of this tool.)


## Formatting

See [test_input.py](./test_input.py) and [test_output.py](./test_output.py)
for a before-and-after example of the tool's behavior when run with the
`--force-triple-quotes` option.

This tool searches the given source files for lines longer than 
max-doc-length appearing in docstrings or block comments. If it finds one, 
it rewraps that line and the remainder of its "paragraph" to fit within 
the maximum, using Python's [textwrap]. The tool only wraps the paragraph
starting at the long line; it doesn't attempt to look back to re-fill the
entire paragraph.

A "paragraph" ends at any of these:
* A blank line or the end of the docstring
* A change in indentation
* A new list item (the tool recognizes several styles of bulleted and
  numbered/lettered lists, which it will wrap preserving hanging indents)
* A line ending in `:` (which often introduces code examples or other text
  that shouldn't be filled)
* A doctest line starting with `>>>`

Lines containing `# noqa` (in any capitalization) are ignored.

The autofix_w505 script processes:

* Block comments: comments which appear on lines without any preceding code.
  (That is, the first non-whitespace character on each line is `#`. This tool 
  does not wrap line-end comments that follow code.)

* Docstrings: string constants that appear at the top of a module or 
  immediately inside a class or function definition (ignoring any intervening 
  comments). Docstrings can use any style of quoting, including raw strings 
  starting with `r` (but not f-strings, which aren't technically constants so
  cannot be docstrings). The tool uses Python's AST to recognize docstrings 
  and will not modify other triple-quoted strings elsewhere in the code.

If a single-line docstring is too long, it is converted to at least three 
lines: opening `"""`, the text (which may wrap to multiple lines), and closing 
`"""`. The new lines are indented to match the opening quotes.

In a multi-line docstring, the opening and closing triple quotes are kept on 
separate lines or left inline with other text, whichever matches the original 
formatting of that docstring.

With the `--force-triple-quotes` option, *all* docstrings are converted to
`"""` triple-double-quotes. Otherwise, single-line docstrings quoted with `"`,
`'` or `'''` are left unchanged if they fit within the maximum length.

The tool wraps lines only at spaces. It will not break words at hyphens or
mid-word. A single word longer than the maximum length (e.g., a long URL) will 
be moved to its own line but not otherwise wrapped.

Source files are assumed to use spaces only and not have trailing whitespace 
on any line. Behavior with files that use tab indentation is undefined.


## Alternatives

[docformatter] is a PEP 257 compliant, robust, well-tested Python docstring 
formatter with several options to control its behavior. It handles docstrings
only, not block comments. And it rewraps all docstrings to maximally fill the
available line length.


[autofix_w505.py]: https://raw.githubusercontent.com/medmunds/autofix-w505/refs/heads/main/autofix_w505.py
[docformatter]: https://pypi.org/project/docformatter/
[textwrap]: https://docs.python.org/3/library/textwrap.html
