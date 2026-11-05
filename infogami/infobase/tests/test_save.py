import datetime
import json
import queue
import re
import threading
import time
import uuid

import pytest
import web

from infogami.infobase._dbstore.save import IndexUtil, PropertyManager, SaveImpl
from infogami.infobase.tests import utils
from infogami.infobase.tests.pytest_wildcard import wildcard  # noqa: F401


def setup_module(mod):
    utils.setup_db(mod)


def teardown_module(mod):
    utils.teardown_db(mod)


class DBTest:
    def setup_method(self, method):
        self.tx = db.transaction()
        db.insert("thing", key='/type/type')
        db.insert("thing", key='/type/object')

    def teardown_method(self, method):
        self.tx.rollback()


def update_doc(doc, revision, created, last_modified):
    """Add revision, latest_revision, created and latest_revision properties to the given doc."""
    last_modified_repr = {"type": "/type/datetime", "value": last_modified.isoformat()}
    created_repr = {"type": "/type/datetime", "value": created.isoformat()}

    return dict(
        doc,
        revision=revision,
        latest_revision=revision,
        created=created_repr,
        last_modified=last_modified_repr,
    )


def assert_record(record, doc, revision, created, timestamp):
    d = update_doc(doc, revision, created, timestamp)
    assert record.data == d

    assert record.key == doc['key']
    assert record.created == created
    assert record.last_modified == timestamp
    assert record.revision == revision

    if revision == 1:
        assert record.id is None
        assert record.prev.data is None
    else:
        assert record.id is not None
        assert record.prev.data is not None


class Test_get_records_for_save(DBTest):
    """Tests for _dbstore_save._get_records_for_save."""

    def test_new(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)

        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        b = {"key": "/b", "type": {"key": "/type/object"}, "title": "b"}

        docs = [a, b]
        records = s._get_records_for_save(docs, timestamp)

        assert len(records) == 2
        assert_record(records[0], docs[0], 1, timestamp, timestamp)
        assert_record(records[1], docs[1], 1, timestamp, timestamp)

    def test_existing(self):
        def insert(doc, revision, created, last_modified):
            id = db.insert(
                'thing',
                key=doc['key'],
                latest_revision=revision,
                created=created,
                last_modified=last_modified,
            )
            db.insert(
                'data',
                seqname=False,
                thing_id=id,
                revision=revision,
                data=json.dumps(doc),
            )

        created = datetime.datetime(2010, 1, 1, 1, 1, 1)
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        insert(a, 1, created, created)

        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 2, 2, 2, 2, 2)
        records = s._get_records_for_save([a], timestamp)

        assert_record(records[0], a, 2, created, timestamp)


class Test_save(DBTest):
    def get_json(self, key):
        d = db.query(
            "SELECT data.data FROM thing, data WHERE data.thing_id=thing.id AND data.revision = thing.latest_revision AND thing.key = '/a'"
        )
        return json.loads(d[0].data)

    def test_save(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}

        status = s.save(
            [a],
            timestamp=timestamp,
            ip="1.2.3.4",
            author=None,
            comment="Testing create.",
            action="save",
        )

        assert status['changes'][0]['revision'] == 1
        assert self.get_json('/a') == update_doc(a, 1, timestamp, timestamp)

        a['title'] = 'b'
        timestamp2 = datetime.datetime(2010, 2, 2, 2, 2, 2)
        status = s.save(
            [a],
            timestamp=timestamp2,
            ip="1.2.3.4",
            author=None,
            comment="Testing update.",
            action="save",
        )
        assert status['changes'][0]['revision'] == 2
        assert self.get_json('/a') == update_doc(a, 2, timestamp, timestamp2)

    def test_type_change(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        status = s.save(
            [a],
            timestamp=timestamp,
            ip="1.2.3.4",
            author=None,
            comment="Testing create.",
            action="save",
        )

        # insert new type
        type_delete_id = db.insert("thing", key='/type/delete')
        a['type']['key'] = '/type/delete'

        timestamp2 = datetime.datetime(2010, 2, 2, 2, 2, 2)
        status = s.save(
            [a],
            timestamp=timestamp2,
            ip="1.2.3.4",
            author=None,
            comment="Testing type change.",
            action="save",
        )

        assert status['changes'][0]['revision'] == 2
        assert self.get_json('/a') == update_doc(a, 2, timestamp, timestamp2)

        thing = db.select("thing", where="key='/a'")[0]
        assert thing.type == type_delete_id

    def test_with_author(self):
        pass

    def test_versions(self):
        pass

    def _get_book_author(self, n):
        author = {
            "key": "/author/%d" % n,
            "type": {"key": "/type/object"},
            "name": "author %d" % n,
        }
        book = {
            "key": "/book/%d" % n,
            "type": {"key": "/type/object"},
            "author": {"key": "/author/%d" % n},
        }
        return author, book

    def test_save_with_cross_refs(self):
        author, book = self._get_book_author(1)
        self._save([author, book])

        author, book = self._get_book_author(2)
        self._save([book, author])

    def _save(self, docs):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        return s.save(
            docs,
            timestamp=timestamp,
            comment="foo",
            ip="1.2.3.4",
            author=None,
            action="save",
        )

    def test_save_with_new_type(self):
        docs = [
            {"key": "/type/foo", "type": {"key": "/type/type"}},
            {"key": "/foo", "type": {"key": "/type/foo"}},
        ]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)

        s.save(
            docs,
            timestamp=timestamp,
            comment="foo",
            ip="1.2.3.4",
            author=None,
            action="save",
        )

        type = db.query("SELECT * FROM thing where key='/type/foo'")[0]
        thing = db.query("SELECT * FROM thing where key='/foo'")[0]
        assert thing.type == type.id

    def test_save_with_all_datatypes(self):
        doc = {
            "key": "/foo",
            "type": {"key": "/type/object"},
            "xtype": {"key": "/type/object"},
            "int": 1,
            "str": "foo",
            "text": {"type": "/type/text", "value": "foo"},
            "date": {"type": "/type/datetime", "value": "2010-01-02T03:04:05"},
        }
        self._save([doc])

    def test_save_with_long_string(self):
        docs = [
            {"key": "/type/foo", "type": {"key": "/type/type"}, "title": "a" * 4000}
        ]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        s.save(
            docs,
            timestamp=timestamp,
            comment="foo",
            ip="1.2.3.4",
            author=None,
            action="save",
        )

    def test_transaction(self, wildcard):
        docs = [
            {
                "key": "/foo",
                "type": {"key": "/type/object"},
            }
        ]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        changeset = s.save(
            docs,
            timestamp=timestamp,
            comment="foo",
            ip="1.2.3.4",
            author=None,
            action="save",
        )
        changeset.pop("docs")
        changeset.pop("old_docs")

        assert changeset == {
            "id": wildcard,
            "kind": "save",
            "timestamp": timestamp.isoformat(),
            "bot": False,
            "comment": "foo",
            "ip": "1.2.3.4",
            "author": None,
            "changes": [{"key": "/foo", "revision": 1}],
            "data": {},
        }


def test_load_records_locks_things_before_loading_data():
    thing = web.storage(id=1, key="/race", latest_revision=2)
    current_data = {
        "key": "/race",
        "type": {"key": "/type/object"},
        "title": "latest",
    }

    class FakeDB:
        def __init__(self):
            self.queries = []

        def query(self, query, vars):
            self.queries.append(query)
            if len(self.queries) == 1:
                return [thing]
            return [web.storage(thing_id=1, data=json.dumps(current_data))]

    fake_db = FakeDB()
    records = SaveImpl(fake_db)._load_records(["/race"])

    locking_query = " ".join(fake_db.queries[0].lower().split())
    data_query = " ".join(fake_db.queries[1].lower().split())
    assert re.search(r"\bfrom\s+thing\s+where\b", locking_query)
    assert "for update nowait" in locking_query
    assert not re.search(r"\bjoin\s+data\b|,\s*data\b", locking_query)
    assert re.search(r"\bfrom\s+thing\s*,\s*data\b", data_query)
    assert re.search(r"data\.thing_id\s*=\s*thing\.id", data_query)
    assert re.search(r"data\.revision\s*=\s*thing\.latest_revision", data_query)
    assert "for update" not in data_query
    assert records["/race"].revision == 2
    assert records["/race"].data == current_data


class _GatedDB:
    def __init__(self, connection, gate_function):
        self.connection = connection
        self.gate_function = gate_function

    def query(self, query, *args, **kwargs):
        if "FOR UPDATE NOWAIT" in query:
            query = query.replace(
                " FOR UPDATE NOWAIT",
                f" AND {self.gate_function}() FOR UPDATE NOWAIT",
            )
        return self.connection.query(query, *args, **kwargs)


class _PostgresSaveRace:
    def __init__(self):
        self.lock_id = uuid.uuid4().int % (2**62)
        self.gate_function = f"infogami_test_gate_{uuid.uuid4().hex}"
        self.key = f"/race-test/{uuid.uuid4().hex}"
        self.db_setup = web.database(**utils.db_parameters)
        self.db_writer = web.database(**utils.db_parameters)
        self.db_control = web.database(**utils.db_parameters)
        self.thing_id = None
        self.function_created = False
        self.control_lock_held = False
        self.worker = None
        self.worker_pid_queue = queue.Queue()
        self.result_queue = queue.Queue()

    def setup(self):
        self.thing_id = self.db_setup.insert("thing", key=self.key, latest_revision=1)
        old_data = {"key": self.key, "type": {"key": "/type/object"}, "title": "before"}
        self.db_setup.insert(
            "data",
            seqname=False,
            thing_id=self.thing_id,
            revision=1,
            data=json.dumps(old_data),
        )
        self.db_control.query(
            f"CREATE FUNCTION {self.gate_function}() RETURNS boolean "
            f"LANGUAGE plpgsql VOLATILE "
            f"AS 'BEGIN PERFORM pg_advisory_lock({self.lock_id}); RETURN TRUE; END;'"
        )
        self.function_created = True
        self.db_control.query(
            "SELECT pg_advisory_lock($lock_id)", vars={"lock_id": self.lock_id}
        )
        self.control_lock_held = True

    def _load_record(self):
        db_reader = web.database(**utils.db_parameters)
        try:
            pid = db_reader.query("SELECT pg_backend_pid() AS pid")[0].pid
            self.worker_pid_queue.put(pid)
            transaction = db_reader.transaction()
            try:
                database = _GatedDB(db_reader, self.gate_function)
                records = SaveImpl(database)._load_records([self.key])
                self.result_queue.put(records)
            except BaseException as error:
                self.result_queue.put(error)
            finally:
                transaction.rollback()
        finally:
            db_reader.ctx.clear()

    def start_reader(self):
        self.worker = threading.Thread(target=self._load_record, daemon=True)
        self.worker.start()
        return self.worker_pid_queue.get(timeout=10)

    def wait_for_lock_gate(self, worker_pid):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            activity = list(
                self.db_control.query(
                    "SELECT wait_event_type, wait_event FROM pg_stat_activity WHERE pid=$pid",
                    vars={"pid": worker_pid},
                )
            )
            if (
                activity
                and activity[0].wait_event_type == "Lock"
                and activity[0].wait_event == "advisory"
            ):
                return
            time.sleep(0.01)
        raise AssertionError("Reader did not reach the test advisory-lock gate")

    def commit_concurrent_revision(self):
        transaction = self.db_writer.transaction()
        new_data = {"key": self.key, "type": {"key": "/type/object"}, "title": "after"}
        self.db_writer.query(
            "UPDATE thing SET latest_revision=2 WHERE id=$thing_id",
            vars={"thing_id": self.thing_id},
        )
        self.db_writer.insert(
            "data",
            seqname=False,
            thing_id=self.thing_id,
            revision=2,
            data=json.dumps(new_data),
        )
        transaction.commit()

    def finish_reader(self):
        self.db_control.query(
            "SELECT pg_advisory_unlock($lock_id)", vars={"lock_id": self.lock_id}
        )
        self.control_lock_held = False
        self.worker.join(timeout=10)
        if self.worker.is_alive():
            raise AssertionError("Reader did not finish after releasing the test gate")
        result = self.result_queue.get_nowait()
        if isinstance(result, BaseException):
            raise result
        return result[self.key]

    def close(self):
        if self.control_lock_held:
            self.db_control.query(
                "SELECT pg_advisory_unlock($lock_id)", vars={"lock_id": self.lock_id}
            )
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=10)
        if self.function_created:
            self.db_control.query(f"DROP FUNCTION IF EXISTS {self.gate_function}()")
        if self.thing_id is not None:
            self.db_setup.delete(
                "data", where="thing_id=$thing_id", vars={"thing_id": self.thing_id}
            )
            self.db_setup.delete(
                "thing", where="id=$thing_id", vars={"thing_id": self.thing_id}
            )
        for connection in (self.db_setup, self.db_writer, self.db_control):
            connection.ctx.clear()


def test_load_records_sees_data_committed_after_lock_query_snapshot():
    """A separate transaction can commit between snapshot acquisition and row locking."""
    race = _PostgresSaveRace()
    try:
        race.setup()
        worker_pid = race.start_reader()
        # The test-only SQL gate blocks after statement-snapshot acquisition but before locking.
        race.wait_for_lock_gate(worker_pid)
        race.commit_concurrent_revision()
        record = race.finish_reader()
        assert record.revision == 2
        assert record.data["title"] == "after"
    finally:
        race.close()


class MockDB:
    def __init__(self):
        self.reset()

    def delete(self, table, vars={}, **kw):
        self.deletes.append(dict(kw, table=table))

    def insert(self, table, **kw):
        self.inserts.append(dict(kw, table=table))

    def reset(self):
        self.inserts = []
        self.deletes = []


class MockSchema:
    def find_table(self, type, datatype, name):
        return "datum_" + datatype


@pytest.fixture()
def testdata(request):
    return {
        "doc1": {
            "key": "/doc1",
            "type": {"key": "/type/object"},
            "xtype": {"key": "/type/object"},
            "x": "x0",
            "y": ["y1", "y2"],
            "z": {"a": "za", "b": "zb"},
            "n": 5,
            "text": {"type": "/type/text", "value": "foo"},
        },
        "doc1.index": {
            ("/type/object", "/doc1", "int", "n"): [5],
            ("/type/object", "/doc1", "ref", "xtype"): ['/type/object'],
            ("/type/object", "/doc1", "str", "x"): ["x0"],
            ("/type/object", "/doc1", "str", "y"): ["y1", "y2"],
            ("/type/object", "/doc1", "str", "z.a"): ["za"],
            ("/type/object", "/doc1", "str", "z.b"): ["zb"],
        },
    }


class TestIndex:
    def setup_method(self, method):
        self.indexer = IndexUtil(MockDB(), MockSchema())

    def monkeypatch_indexer(self):
        self.indexer.get_thing_ids = lambda keys: {k: "id:" + k for k in keys}
        self.indexer.get_property_id = lambda type, name: "p:{}-{}".format(
            type.split("/")[-1],
            name,
        )
        self.indexer.get_table = lambda type, datatype, name: "{}_{}".format(
            type.split("/")[-1],
            datatype,
        )

    def test_monkeypatch(self):
        self.monkeypatch_indexer()
        assert self.indexer.get_thing_ids(["a", "b"]) == {"a": "id:a", "b": "id:b"}
        assert self.indexer.get_property_id("/type/book", "title") == "p:book-title"
        assert self.indexer.get_table("/type/book", "foo", "bar") == "book_foo"

    def process_index(self, index):
        """Process index to remove order in the values, so that it is easier to compare."""
        return {k: set(v) for k, v in index.items()}

    def test_compute_index(self, testdata):
        index = self.indexer.compute_index(testdata['doc1'])
        assert self.process_index(index) == self.process_index(testdata['doc1.index'])

    def test_dict_difference(self):
        f = self.indexer._dict_difference
        d1 = {"w": 1, "x": 2, "y": 3}
        d2 = {"x": 2, "y": 4, "z": 5}

        assert f(d1, d2) == {"w": 1, "y": 3}
        assert f(d2, d1) == {"y": 4, "z": 5}

    def test_diff_index(self):
        doc1 = {
            "key": "/books/1",
            "type": {"key": "/type/book"},
            "title": "foo",
            "author": {"key": "/authors/1"},
        }
        doc2 = dict(doc1, title='bar')

        deletes, inserts = self.indexer.diff_index(doc1, doc2)
        assert deletes == {("/type/book", "/books/1", "str", "title"): ["foo"]}
        assert inserts == {("/type/book", "/books/1", "str", "title"): ["bar"]}

        deletes, inserts = self.indexer.diff_index(None, doc1)
        assert deletes == {}
        assert inserts == {
            ("/type/book", "/books/1", "ref", "author"): ["/authors/1"],
            ("/type/book", "/books/1", "str", "title"): ["foo"],
        }

        # when type is changed all the old properties must be deleted
        doc2 = dict(doc1, type={"key": "/type/object"})
        deletes, inserts = self.indexer.diff_index(doc1, doc2)
        assert deletes == {
            ("/type/book", "/books/1", "ref", None): [],
            ("/type/book", "/books/1", "str", None): [],
            ("/type/book", "/books/1", "int", None): [],
        }

    def test_diff_records(self):
        doc1 = {
            "key": "/books/1",
            "type": {"key": "/type/book"},
            "title": "foo",
            "author": {"key": "/authors/1"},
        }
        doc2 = dict(doc1, title='bar')
        record = web.storage(key='/books/1', data=doc2, prev=web.storage(data=doc1))

        deletes, inserts = self.indexer.diff_records([record])
        assert deletes == {("/type/book", "/books/1", "str", "title"): ["foo"]}
        assert inserts == {("/type/book", "/books/1", "str", "title"): ["bar"]}

    def test_compile_index(self):
        self.monkeypatch_indexer()

        index = {
            ("/type/book", "/books/1", "str", "name"): ["Getting started with py.test"],
            ("/type/book", "/books/2", "ref", "author"): ["/authors/1"],
        }
        self.indexer.compile_index(index) == {
            ("book_str", "id:/books/1", "p:book-name"): [
                "Getting started with py.test"
            ],
            ("book_ref", "id:/books/2", "p:book-author"): ["id:/authors/1"],
        }

        # When the type is changed, property_name will be None to indicate that all the properties are to be removed.
        index = {("/type/books", "/books/1", "str", None): []}
        self.indexer.compile_index(index) == {("book_str", "id:/books/1", None): []}

    def test_too_long(self):
        assert self.indexer._is_too_long("a" * 10000) is True
        assert self.indexer._is_too_long("a" * 2047) is False
        c = '\u20AC'  # 3 bytes in utf-8
        assert self.indexer._is_too_long(c * 1000) is False


class TestIndexWithDB(DBTest):
    def _save(self, docs):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 1, 1, 1, 1, 1)
        return s.save(
            docs,
            timestamp=timestamp,
            comment="foo",
            ip="1.2.3.4",
            author=None,
            action="save",
        )

    def test_reindex(self):
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        self._save([a])

        thing = db.query("SELECT * FROM thing WHERE key='/a'")[0]
        key_id = db.query(
            "SELECT * FROM property WHERE type=$thing.type AND name='title'",
            vars=locals(),
        )[0].id

        # there should be only one entry in the index
        d = db.query(
            "SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",
            vars=locals(),
        )
        assert len(d) == 1

        # corrupt the index table by adding bad entries
        for i in range(10):
            db.insert("datum_str", thing_id=thing.id, key_id=key_id, value="foo %d" % i)

        # verify that the bad entries are added
        d = db.query(
            "SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",
            vars=locals(),
        )
        assert len(d) == 11

        # reindex now and verify again that there is only one entry
        SaveImpl(db).reindex(["/a"])
        d = db.query(
            "SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",
            vars=locals(),
        )
        assert len(d) == 1


class TestPropertyManager(DBTest):
    global db

    def test_get_property_id(self):
        p = PropertyManager(db)
        assert p.get_property_id("/type/object", "title") is None

        pid = p.get_property_id("/type/object", "title", create=True)
        assert pid is not None

        assert p.get_property_id("/type/object", "title") == pid
        assert p.get_property_id("/type/object", "title", create=True) == pid

    def test_rollback(self):
        # cache is not invalidated on rollback. This test confirms that behavior.

        tx = db.transaction()
        p = PropertyManager(db)
        pid = p.get_property_id("/type/object", "title", create=True)
        tx.rollback()

        assert p.get_property_id("/type/object", "title") == pid

    def test_copy(self):
        p = PropertyManager(db)
        pid = p.get_property_id("/type/object", "title", create=True)

        # copy should inherit the cache
        p2 = p.copy()
        assert p2.get_property_id("/type/object", "title") == pid

        # changes to the cache of the copy shouldn't affect the source.
        tx = db.transaction()
        p2.get_property_id("/type/object", "title2", create=True)
        tx.rollback()
        assert p.get_property_id("/type/object", "title2") is None
