"""``find_datatype`` and its per-property datatype cache.

The cache is keyed on the type document's revision, so these tests care about
two things: that a repeated lookup stops touching the store, and that nothing
can be served from an entry belonging to a different revision, site or
property.
"""

import json

import pytest

from infogami.infobase import lru, readquery
from infogami.infobase.core import Thing


class FakeStore:
    """Minimal store that records which keys were looked up."""

    def __init__(self, docs, sitename=None):
        self.docs = docs
        self.sitename = sitename
        self.requested = []

    def get(self, key):
        self.requested.append(key)
        return json.dumps(self.docs[key])


def property_dict(name, expected_type):
    return {
        'name': name,
        'expected_type': {'key': expected_type},
        'type': {'key': '/type/property'},
    }


def make_type(properties, revision=1, sitename=None, key='/type/edition'):
    """A type Thing backed by a store holding every expected_type it names."""
    docs = {'/type/property': {'key': '/type/property'}}
    for p in properties:
        docs[p['expected_type']['key']] = {'key': p['expected_type']['key']}

    data = {'key': key, 'type': {'key': '/type/type'}, 'properties': properties}
    if revision is not None:
        data['revision'] = revision

    store = FakeStore(docs, sitename=sitename)
    return store, Thing.from_dict(store, key, data)


EDITION_PROPERTIES = [
    property_dict('title', '/type/string'),
    property_dict('number_of_pages', '/type/int'),
    property_dict('works', '/type/work'),
]


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    """Each test gets its own cache; the module-level one is process-wide.

    ``raising=False`` so the behaviour tests in this module still run against a
    build with no cache at all, and report a real result instead of erroring on
    a missing attribute.
    """
    monkeypatch.setattr(readquery, "_datatype_cache", lru.LRU(1000), raising=False)


class TestFindDatatypeResult:
    """The returned datatype, which the cache must not change."""

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('title', 'str'),
            ('number_of_pages', 'int'),
            ('works', 'ref'),
        ],
    )
    def test_datatype_comes_from_the_type_schema(self, name, expected):
        _, type_ = make_type(EDITION_PROPERTIES)

        assert readquery.find_datatype(type_, name, None) == expected

    def test_an_unknown_property_is_a_string(self):
        _, type_ = make_type(EDITION_PROPERTIES)

        assert readquery.find_datatype(type_, 'no_such_property', None) == 'str'

    def test_no_type_is_a_string(self):
        assert readquery.find_datatype(None, 'title', 'hello') == 'str'

    @pytest.mark.parametrize(
        ('key', 'expected'),
        [('key', 'key'), ('type', 'ref'), ('created', 'datetime')],
    )
    def test_special_properties_bypass_the_schema(self, key, expected):
        store, type_ = make_type(EDITION_PROPERTIES)

        assert readquery.find_datatype(type_, key, None) == expected
        assert store.requested == []

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [(True, 'boolean'), (3, 'int'), (1.5, 'float')],
    )
    def test_the_value_decides_before_the_schema(self, value, expected):
        _, type_ = make_type(EDITION_PROPERTIES)

        assert readquery.find_datatype(type_, 'title', value) == expected


class TestDatatypeCache:
    def test_a_repeated_lookup_does_not_touch_the_store(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        assert readquery.find_datatype(type_, 'title', None) == 'str'
        after_first = list(store.requested)
        assert after_first, "the first lookup should resolve expected_type"

        assert readquery.find_datatype(type_, 'title', None) == 'str'

        assert store.requested == after_first

    def test_each_property_is_cached_separately(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        readquery.find_datatype(type_, 'title', None)
        store.requested.clear()

        assert readquery.find_datatype(type_, 'number_of_pages', None) == 'int'
        assert store.requested, "a different property must not reuse another's entry"

    def test_an_unknown_property_stays_free(self):
        """Already free before the cache (nothing to resolve); must stay free."""
        store, type_ = make_type(EDITION_PROPERTIES)

        readquery.find_datatype(type_, 'no_such_property', None)
        store.requested.clear()

        assert readquery.find_datatype(type_, 'no_such_property', None) == 'str'
        assert store.requested == []

    def test_a_new_revision_is_not_served_from_the_old_entry(self):
        _, old = make_type([property_dict('title', '/type/string')], revision=1)
        assert readquery.find_datatype(old, 'title', None) == 'str'

        # Same type key, same property, edited to a different expected_type.
        _, new = make_type([property_dict('title', '/type/int')], revision=2)

        assert readquery.find_datatype(new, 'title', None) == 'int'

    def test_two_sites_do_not_share_an_entry(self):
        _, a = make_type(
            [property_dict('title', '/type/string')], revision=1, sitename='a'
        )
        assert readquery.find_datatype(a, 'title', None) == 'str'

        _, b = make_type(
            [property_dict('title', '/type/int')], revision=1, sitename='b'
        )

        assert readquery.find_datatype(b, 'title', None) == 'int'

    def test_a_type_without_a_revision_is_never_cached(self):
        store, type_ = make_type(EDITION_PROPERTIES, revision=None)

        readquery.find_datatype(type_, 'title', None)
        after_first = list(store.requested)
        store.requested.clear()

        assert readquery.find_datatype(type_, 'title', None) == 'str'
        assert (
            store.requested == after_first
        ), "with no revision to key on, the result must be recomputed"
