#!/bin/sh

# USER=openlibrary@example.com pytest --doctest-modules || true

USER=openlibrary@example.com pytest --doctest-modules \
    --ignore=infogami/infobase/_json.py \
    --ignore=infogami/infobase/tests/test_account.py \
    --ignore=infogami/infobase/tests/test_client.py \
    --ignore=infogami/infobase/tests/test_infobase.py \
    --ignore=infogami/infobase/tests/test_read.py \
    --ignore=infogami/infobase/tests/test_save.py \
    --ignore=infogami/infobase/tests/test_seq.py \
    --ignore=infogami/infobase/tests/test_store.py \
    --ignore=infogami/infobase/tests/test_writequery.py \
    --ignore=infogami/plugins/wikitemplates/code.py  \
    --ignore=migration/migrate-0.4-0.5.py \
    --ignore=test/bug_239238.py \
    --ignore=test/test_dbstore.py
