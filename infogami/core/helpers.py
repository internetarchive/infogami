"""
Generic Utilities.
"""

import re


class xdict:
    """Dictionary wrapper to give sorted repr.
    Used for doctest.
    """

    def __init__(self, d):
        self.d = d

    def __repr__(self):
        def f(d):
            if isinstance(d, dict):
                return xdict(d)
            else:
                return d

        return (
            '{' + ", ".join([f"'{k}': {f(v)}" for k, v in sorted(self.d.items())]) + '}'
        )


def flatten(d):
    """Make a dictionary flat.

    >>> d = {'a': 1, 'b': [2, 3], 'c': {'x': 4, 'y': 5}}
    >>> xdict(flatten(d))
    {'a': 1, 'b#0': 2, 'b#1': 3, 'c.x': 4, 'c.y': 5}
    """

    def traverse(d, prefix, delim, visit):
        for k, v in d.items():
            k = str(k)
            if isinstance(v, dict):
                traverse(v, prefix + delim + k, '.', visit)
            elif isinstance(v, list):
                traverse(betterlist(v), prefix + delim + k, '#', visit)
            else:
                visit(prefix + delim + k, v)

    def visit(k, v):
        d2[k] = v

    d2 = {}
    traverse(d, "", "", visit)
    return d2


def unflatten(d):
    """Inverse of flatten.

    >>> xdict(unflatten({'a': 1, 'b#0': 2, 'b#1': 3, 'c.x': 4, 'c.y': 5}))
    {'a': 1, 'b': [2, 3], 'c': {'x': 4, 'y': 5}}
    >>> unflatten({'a#1#2.b': 1})
    {'a': [None, [None, None, {'b': 1}]]}

    The blank "template" row of a repeated field (see
    number_template_rows) becomes a new item at the end of its list:

    >>> unflatten({'a#0': 'x', 'a#[row_a]': 'y'})
    {'a': ['x', 'y']}
    """
    d = number_template_rows(d)

    def setdefault(d, k, v):
        # error check: This can happen when d has both foo.x and foo as keys
        if not isinstance(d, (dict, betterlist)):
            return

        if '.' in k:
            a, b = k.split('.', 1)
            return setdefault(setdefault(d, a, {}), b, v)
        elif '#' in k:
            a, b = k.split('#', 1)
            return setdefault(setdefault(d, a, betterlist()), b, v)
        else:
            return d.setdefault(k, v)

    d2 = {}
    for k, v in d.items():
        setdefault(d2, k, v)
    return d2


_LIST_INDEX = re.compile(r'#(\d+|\[row_[^\]]*\])')


def number_template_rows(d):
    """Replace template-row indices like ``foo#[row_foo]`` with real ones.

    For every repeated field, default_edit.html renders one extra blank row
    whose inputs are named ``<field>#[row_<field>]...``. The repetition JS
    is meant to disable that row before the form is submitted, but when the
    JS doesn't run the row is posted too. It then gets the index after the
    last existing row of the same list, so a value typed into it is added as
    a new item, and a row left blank is removed later by edit.trim.

    >>> sorted(number_template_rows({'a#0': 'x', 'a#1': 'y', 'a#[row_a]': 'z'}).items())
    [('a#0', 'x'), ('a#1', 'y'), ('a#2', 'z')]

    All fields of an embeddable template row share one new index, numbered
    per list:

    >>> sorted(number_template_rows({
    ...     'a#0.x': '1', 'a#[row_a].x': '2', 'a#[row_a].y': '3',
    ...     'b#[row_b]': '4',
    ... }).items())
    [('a#0.x', '1'), ('a#1.x', '2'), ('a#1.y', '3'), ('b#0', '4')]

    Keys without a template row are returned unchanged:

    >>> number_template_rows({'a#0': 'x', 'b': 'y'})
    {'a#0': 'x', 'b': 'y'}
    """
    if not any('#[row_' in k for k in d):
        return d

    # Highest existing index for each list, keyed by the path before the '#'.
    last_index = {}
    for k in d:
        for m in _LIST_INDEX.finditer(k):
            if not m.group(1).isdigit():
                break
            path = k[: m.start()]
            last_index[path] = max(last_index.get(path, -1), int(m.group(1)))

    def renumber(k):
        out, pos = '', 0
        for m in _LIST_INDEX.finditer(k):
            out += k[pos : m.start()]
            index = m.group(1)
            if not index.isdigit():
                index = str(last_index.get(out, -1) + 1)
            out += '#' + index
            pos = m.end()
        return out + k[pos:]

    return {renumber(k): v for k, v in d.items()}


class betterlist(list):
    """List with dict like setdefault method."""

    def fill(self, size):
        while len(self) < size:
            self.append(None)

    def setdefault(self, index, value):
        index = int(index)
        self.fill(index + 1)
        if self[index] is None:
            self[index] = value
        return self[index]

    def iteritems(self):
        return enumerate(self)

    def items(self):
        return list(self.iteritems())  # Works on both Python 2 and 3


def trim(x):
    """Remove empty elements from a list or dictionary.

    >>> trim([2, 3, None, None, '', 42])
    [2, 3, 42]
    >>> trim([{'x': 1}, {'x': ''}, {'x': 3}])
    [{'x': 1}, {'x': 3}]
    >>> trim({'x': 1, 'y': '', 'z': ['a', '', 'b']})
    {'x': 1, 'z': ['a', 'b']}
    >>> trim(unflatten({'a#1#2.b': 1}))
    {'a': [[{'b': 1}]]}
    >>> trim(flatten(unflatten({'a#1#2.b': 1})))
    {'a#1#2.b': 1}
    """

    def trimlist(x):
        y = []
        for v in x:
            if isinstance(v, list):
                v = trimlist(v)
            elif isinstance(v, dict):
                v = trimdict(v)
            if v:
                y.append(v)
        return y

    def trimdict(x):
        y = {}
        for k, v in x.items():
            if isinstance(v, list):
                v = trimlist(v)
            elif isinstance(v, dict):
                v = trimdict(v)
            if v:
                y[k] = v
        return y

    if isinstance(x, list):
        return trimlist(x)
    elif isinstance(x, dict):
        return trimdict(x)
    else:
        return x


def subdict(d, keys):
    """Subset like operation on dictionary.

    >>> subdict({'a': 1, 'b': 2, 'c': 3}, ['a', 'c'])
    {'a': 1, 'c': 3}
    >>> subdict({'a': 1, 'b': 2, 'c': 3}, ['a', 'c', 'd'])
    {'a': 1, 'c': 3}
    """
    return {k: d[k] for k in keys if k in d}


if __name__ == "__main__":
    import doctest

    doctest.testmod()
