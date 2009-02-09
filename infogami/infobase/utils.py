"""Generic utilities.
"""
import datetime
import re
import web

try:
    from __builtin__ import any, all
except ImportError:
    def any(seq):
        for x in seq:
            if x:
                return True
                
    def all(seq):
        for x in seq:
            if not x:
                return False
        return True

def parse_datetime(value):
    """Creates datetime object from isoformat.
    
        >>> t = '2008-01-01T01:01:01.010101'
        >>> parse_datetime(t).isoformat()
        '2008-01-01T01:01:01.010101'
    """
    if isinstance(value, datetime.datetime):
        return value
    else:
        tokens = re.split('-|T|:|\.| ', value)
        return datetime.datetime(*map(int, tokens))
    
def parse_boolean(value):
    return web.safeunicode(value).lower() in ["1", "true"]

def dict_diff(d1, d2):
    """Compares 2 dictionaries and returns the following.
    
        * all keys in d1 whose values are changed in d2
        * all keys in d1 which have same values in d2
        * all keys in d2 whose values are changed in d1
    
        >>> a, b, c = dict_diff({'x': 1, 'y': 2, 'z': 3}, {'x': 11, 'z': 3, 'w': 23})
        >>> sorted(a), sorted(b), sorted(c)
        (['x', 'y'], ['z'], ['w', 'x'])
    """
    same = set(k for k in d1 if d1[k] == d2.get(k))
    left = set(d1.keys()).difference(same)
    right = set(d2.keys()).difference(same)
    return left, same, right
                        
def pprint(obj):
    """Pretty prints given object.
    >>> pprint(1)
    1
    >>> pprint("hello")
    'hello'
    >>> pprint([1, 2, 3])
    [1, 2, 3]
    >>> pprint({'x': 1, 'y': 2})
    {
        'x': 1,
        'y': 2
    }
    >>> pprint([dict(x=1, y=2), dict(c=1, a=2)])
    [{
        'x': 1,
        'y': 2
    }, {
        'a': 2,
        'c': 1
    }]
    >>> pprint({'x': 1, 'y': {'a': 1, 'b': 2}, 'z': 3})
    {
        'x': 1,
        'y': {
            'a': 1,
            'b': 2
        },
        'z': 3
    }
    >>> pprint({})
    {
    }
    """
    print prepr(obj)
    
def prepr(obj, indent=""):
    """Pretty representaion."""
    if isinstance(obj, list):
        return "[" + ", ".join(prepr(x, indent) for x in obj) + "]"
    elif isinstance(obj, tuple):
        return "(" + ", ".join(prepr(x, indent) for x in obj) + ")"
    elif isinstance(obj, dict):
        if hasattr(obj, '__prepr__'):
            return obj.__prepr__()
        else:
            indent = indent + "    "
            items = ["\n" + indent + prepr(k) + ": " + prepr(obj[k], indent) for k in sorted(obj.keys())]
            return '{' + ",".join(items) + "\n" + indent[4:] + "}"
    else:
        return repr(obj)