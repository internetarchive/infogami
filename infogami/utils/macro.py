"""
Macro extension to markdown.

Macros take argument string as input and returns result as markdown text.
"""

import ast
import os
from typing import cast

import web

from infogami.utils import storage, template
from infogami.utils.markdown import markdown

# macros loaded from disk
diskmacros = template.DiskTemplateSource()
# macros specified in the code
codemacros = web.storage()

macrostore = storage.DictPile()
macrostore.add_dict(diskmacros)
macrostore.add_dict(codemacros)


def macro(f):
    """Decorator to register a markdown macro.
    Macro is a function that takes argument string and returns result as markdown string.
    """
    codemacros[f.__name__] = f
    return f


def load_macros(plugin_root, lazy=False):
    """Adds $plugin_root/macros to macro search path."""
    path = os.path.join(plugin_root, 'macros')
    if os.path.isdir(path):
        diskmacros.load_templates(path, lazy=lazy)


# -- macro execution


def macro_eval(macro, macro_call: str) -> str:
    """
    >>> def dummy_macro(*args, **kwargs):
    ...    return 'SUCCESS: ' + repr(args) + ' ' + repr(kwargs)
    >>> macro_eval(dummy_macro, 'foo("hello")')
    "SUCCESS: ('hello',) {}"
    >>> macro_eval(dummy_macro, 'foo(123)')
    'SUCCESS: (123,) {}'
    >>> macro_eval(dummy_macro, 'foo(bar=3.14)')
    "SUCCESS: () {'bar': 3.14}"
    >>> macro_eval(dummy_macro, 'foo()')
    'SUCCESS: () {}'
    >>> macro_eval(dummy_macro, 'foo(evil)')
    'ERROR: Invalid arg: {{foo(evil)}}'
    >>> macro_eval(dummy_macro, 'foo(3*3)')
    'ERROR: Invalid arg: {{foo(3*3)}}'
    >>> macro_eval(dummy_macro, 'foo(web.ctx.site.get("foo"))')
    'ERROR: Invalid arg: {{foo(web.ctx.site.get("foo"))}}'
    >>> macro_eval(dummy_macro, 'foo("hi", this="works")')
    "SUCCESS: ('hi',) {'this': 'works'}"
    >>> macro_eval(dummy_macro, 'foo("hah", 3*3)')
    'ERROR: Invalid arg: {{foo("hah", 3*3)}}'
    >>> macro_eval(dummy_macro, 'foo(nope="hah", this=3*3)')
    'ERROR: Invalid keyword arg: {{foo(nope="hah", this=3*3)}}'
    >>> macro_eval(dummy_macro, 'foo(123)web.ctx.site.get("foo")')
    'ERROR: Invalid macro: {{foo(123)web.ctx.site.get("foo")}}'
    """
    try:
        tree = ast.parse(macro_call)
        assert len(tree.body) == 1
        body_root = tree.body[0]
        assert isinstance(body_root, ast.Expr)
        call_node = body_root.value
        assert isinstance(call_node, ast.Call)
        args = call_node.args
        kwargs = {keyword.arg: keyword.value for keyword in call_node.keywords}
        for arg in args:
            if not isinstance(arg, ast.Constant):
                return "ERROR: Invalid arg: {{" + macro_call + "}}"
        for key, value in kwargs.items():
            assert isinstance(key, str)
            if not isinstance(value, ast.Constant):
                return "ERROR: Invalid keyword arg: {{" + macro_call + "}}"

        # Need these to appease mypy
        args_typed = cast(list[ast.Constant], args)
        kwargs_typed = cast(dict[str, ast.Constant], kwargs)

        return macro(
            *[arg.value for arg in args_typed],
            **{key: value.value for key, value in kwargs_typed.items()},
        )
    except (AssertionError, SyntaxError):
        return "ERROR: Invalid macro: {{" + macro_call + "}}"


def call_macro(name, args):
    if name in macrostore:
        try:
            macro = macrostore[name]
            macro_string = name + "(" + args + ")"
            result = macro_eval(macro, macro_string)
        except Exception as e:
            i = web.input(_method="GET", debug="false")
            if i.debug.lower() == "true":
                raise
            result = f"{name} failed with error: <pre>{web.websafe(str(e))}</pre>"
            import traceback

            traceback.print_exc()
        return str(result)
    else:
        return "Unknown macro: <pre>%s</pre>" % name


MACRO_PLACEHOLDER = "asdfghjjkl%sqwertyuiop"


class MacroPattern(markdown.BasePattern):
    """Inline pattern to replace macros."""

    def __init__(self, md):
        pattern = r'{{([a-zA-Z0-9_]*)\((.*)\)}}'
        markdown.BasePattern.__init__(self, pattern)
        self.markdown = md

    def handleMatch(self, m, doc):
        name, args = m.group(2), m.group(3)

        # markdown uses place-holders to replace html blocks.
        # markdown.HtmlStash stores the html blocks to be replaced
        placeholder = self.store(self.markdown, (name, args))
        return doc.createTextNode(placeholder)

    def store(self, md, macro_info):
        placeholder = MACRO_PLACEHOLDER % md.macro_count
        md.macro_count += 1
        md.macros[placeholder] = macro_info
        return placeholder


def replace_macros(html, macros):
    """Replaces the macro place holders with real macro output."""
    for placeholder, macro_info in macros.items():
        name, args = macro_info
        html = html.replace(
            "<p>%s\n</p>" % placeholder, web.safestr(call_macro(name, args))
        )

    return html


class MacroExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.insert(0, MacroPattern(md))
        md.macro_count = 0
        md.macros = {}


def makeExtension(configs={}):
    return MacroExtension(configs=configs)


# -- sample macros


@macro
def HelloWorld():
    """Hello world macro."""
    return "<b>Hello, world</b>."


@macro
def ListOfMacros():
    """Lists all available macros."""
    out = ""
    out += "<ul>"
    for name, macro in macrostore.items():
        out += '  <li><b>{}</b>: {}</li>\n'.format(name, macro.__doc__ or "")
    out += "</ul>"
    return out


if __name__ == "__main__":
    text = "{{HelloWorld()}}"
    md = markdown.Markdown(source=text, safe_mode=False)
    MacroExtension().extendMarkdown(md, {})
    html = md.convert()
    print(replace_macros(html, md.macros))  # type: ignore
