import json

import pytest

from infogami.infobase.core import Thing


class FakeStore:
    """Minimal store that records which keys were looked up."""

    def __init__(self, docs):
        self.docs = docs
        self.requested = []

    def get(self, key):
        self.requested.append(key)
        return json.dumps(self.docs[key])


def make_type(properties):
    """Build a type Thing backed by a store holding every expected_type it names."""
    docs = {'/type/property': {'key': '/type/property'}}
    for p in properties:
        expected_type = p['expected_type']['key']
        docs[expected_type] = {'key': expected_type}

    store = FakeStore(docs)
    thing = Thing.from_dict(
        store,
        '/type/edition',
        {
            'key': '/type/edition',
            'type': {'key': '/type/type'},
            'properties': properties,
        },
    )
    return store, thing


def property_dict(name, expected_type):
    return {
        'name': name,
        'expected_type': {'key': expected_type},
        'type': {'key': '/type/property'},
    }


EDITION_PROPERTIES = [
    property_dict('title', '/type/string'),
    property_dict('number_of_pages', '/type/int'),
    property_dict('works', '/type/work'),
]


class TestThingGetProperty:
    def test_returns_the_matching_property(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        p = type_.get_property('number_of_pages')

        assert p.name == 'number_of_pages'
        assert p.expected_type.key == '/type/int'

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('title', '/type/string'),
            ('number_of_pages', '/type/int'),
            ('works', '/type/work'),
        ],
    )
    def test_resolves_expected_type_for_every_property(self, name, expected):
        store, type_ = make_type(EDITION_PROPERTIES)

        assert type_.get_property(name).expected_type.key == expected

    def test_returns_none_for_an_unknown_name(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        assert type_.get_property('no_such_property') is None

    def test_returns_none_when_the_type_has_no_properties(self):
        store = FakeStore({})
        type_ = Thing.from_dict(store, '/type/edition', {'key': '/type/edition'})

        assert type_.get_property('title') is None

    def test_does_not_resolve_the_properties_that_do_not_match(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        type_.get_property('title')

        assert store.requested == ['/type/string', '/type/property']

    def test_looks_up_nothing_for_an_unknown_name(self):
        store, type_ = make_type(EDITION_PROPERTIES)

        type_.get_property('no_such_property')

        assert store.requested == []

    def test_returns_the_first_property_when_a_name_is_duplicated(self):
        store, type_ = make_type(
            [
                property_dict('title', '/type/string'),
                property_dict('title', '/type/text'),
            ]
        )

        p = type_.get_property('title')

        assert p.expected_type.key == '/type/string'
        assert store.requested == ['/type/string', '/type/property']
