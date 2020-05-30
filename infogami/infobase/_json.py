r"""
Wrapper to simplejson to fix unicode/utf-8 issues in python 2.4.

See Bug#231831 for details.


    >>> loads(dumps(u'\u1234'))
    u'\u1234'
    >>> loads(dumps(u'\u1234'.encode('utf-8')))
    u'\u1234'
    >>> loads(dumps({'x': u'\u1234'.encode('utf-8')}))
    {u'x': u'\u1234'}
"""
import datetime

import simplejson

class JSONEncoder(simplejson.JSONEncoder):
    def default(self, o):
        if hasattr(o, '__json__'):
            return simplejson.loads(o.__json__())
        else:
            return simplejson.JSONEncoder.default(self, o)

def dumps(obj, **kw):
    """
        >>> class Foo:
        ...     def __json__(self): return 'foo'
        ...
        >>> a = [Foo(), Foo()]
        >>> dumps(a)
        '[foo, foo]'
    """
    return simplejson.dumps(obj, cls=JSONEncoder, **kw)

def loads(s, **kw):
    return simplejson.loads(s, **kw)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
