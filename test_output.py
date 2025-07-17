#!/usr/bin/env/false --shebang-is-not-a-block-comment /so/do/not/try/to/wrap/it --ok?
"""
A module-level docstring is a docstring too. This one needs to be wrapped.
"""

from textwrap import dedent


def foo():
    """A function docstring. This short line doesn't need wrapping.

    But this paragraph includes a longer line
    that does need to be wrapped. The wrapping starts with the long line and
    will re-fill remaining lines in the paragraph as necessary even if some of
    them are already short enough to fit on their own. Rewrapping occurs for
    the entire remainder of the paragraph.

    But rewrapping does not extend into the next paragraph.

    A long URL may be wrapped:
    https://example.com/but-it-does-not-need-to-be-broken-if-too-long-for-a-single-line
    """
    return dedent(
        """
        This is an ordinary triple-quoted string. It does not need to be wrapped.
        """
    )


def bar():
    """A single-quoted docstring is converted to a triple-quoted string."""


def baz():
    """
    Long single-quoted strings may need additional wrapping once converted.
    """


async def bazinga():
    """
    Single-quoted strings may wrap to multiple lines after being converted to
    triple-quoted.
    """


class Foo:
    """
    Here are some tests for bullet and numbered lists.

    - A bullet list item without wrapping.
    - This bullet list item needs to be wrapped paying attention to the
      indentation.
    - This other bullet item needs to be wrapped too,
      but only in its continuation line (so it might as well not be handled as
      a list item).
      - This is a sub-list item, not a continuation of the previous one.
    * A star can also be used for a bullet list. And when a list item is
      wrapped, it refills any continuation lines along with it so that you get
      one nicely wrapped "paragraph" per list item.

        12. Numbered list item that wants some wrapping please, because it is
            too long.
            a. This is sub-item 12a, not part of item 12. Also, letters create
               numbered lists.
            B) Even upper-case letters work. (So this item should be wrapped as
               well.)
        4)  Another style of numbered list item. Whitespace after the number is
            variable.

        42 is just a number, not a numbered list. Ordinary paragraph wrapping
        here.

                    Sometimes a line may start with a number, like
                    22. That might get mis-recognized as a numbered list item,
                        but there's
                    not much we can do about that.
    """

    def foo(self):  # An end-of-line comment is not a block comment. No wrapping here.
        # But this is very much a block comment, so should follow the ordinary
        # wrapping rules.
        #     This is a different paragraph, and should be wrapped separately
        #     with its own indentation.
        pass

    # This line is exactly 79 characters, so it's good without being rewrapped.
    # This line is exactly 80 characters, so it really must be rewrapped to
    # fit.

    async def bar(self):
        """
        There is no special handling for doctest lines, but they are considered
        a separate paragraph.
        >>> "**********" * 8  # This is wrapped as ordinary text, not code. Use
        blacken-docs instead.
        '********************************************************************************'
        """

    def baz(self):
        """
        Exceptions that have been specifically excluded from length rules are
        not wrapped.
        For example, this line can't fill into the previous one.  # NOQA

        https://example.com/we-neeed-to-keep-the-noqa-comment-on-its-original-line  # noqa: W505

        #12345 is a number, not a comment appearing within a docstring. Rewrap
        with care.
        """
        # A line ending in a colon is assumed to introduce a code example or
        # similar:
        # example = True  # not filled into previous line
        #
        #                     The end-of-line colon rule applies equally to
        #                     continuation lines:
        #                     don't fill me


def raw_docstring():
    r"""
    Raw docstrings are used when a \ character appears in the docstring, e.g.,
    for figure drawing.
    """


def raw_single_quoted_docstring():
    r"""
    This needs to get converted to a raw triple-double-quoted string to wrap.
    """
