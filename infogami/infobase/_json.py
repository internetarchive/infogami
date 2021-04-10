r"""
Wrapper to simplejson to fix unicode/utf-8 issues in python 2.4.

See Bug#231831 for details.


    >>> loads(dumps(u'\u1234'))
    u'\u1234'
    >>> loads(dumps(u'\u1234'.encode('utf-8')))
    u'\u1234'
    >>> loads(dumps({u'x': u'\u1234'.encode('utf-8')}))
    {u'x': u'\u1234'}
"""
import datetime

import json
from six import iteritems


def unicodify(d):
    """Converts all utf-8 encoded strings to unicode recursively."""
    if isinstance(d, dict):
        return {k: unicodify(v) for k, v in iteritems(d)}
    elif isinstance(d, list):
        return [unicodify(x) for x in d]
    elif isinstance(d, bytes):
        return d.decode('utf-8')
    elif isinstance(d, datetime.datetime):
        return d.isoformat()
    else:
        return d


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, '__json__'):
            return json.loads(o.__json__())
        else:
            return json.JSONEncoder.default(self, o)


def dumps(obj, **kw):
    """
    >>> class Foo:
    ...     def __json__(self): return 'foo'
    ...
    >>> a = [Foo(), Foo()]
    >>> dumps(a)
    '[foo, foo]'
    """
    return json.dumps(unicodify(obj), cls=JSONEncoder, **kw)


def loads(s, **kw):
    return json.loads(s, **kw)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
