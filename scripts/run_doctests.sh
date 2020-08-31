#!/bin/sh

# platform linux2 -- Python 2.7.6, pytest-4.6.9, py-1.9.0, pluggy-0.13.1
# collected 112 items
# platform linux -- Python 3.8.5, pytest-6.0.1, py-1.9.0, pluggy-0.13.1
# collected 112 items

# To run ALL doctests, use:
# USER=openlibrary@example.com pytest --doctest-modules || true

USER=openlibrary@example.com pytest --doctest-modules \
    --ignore=infogami/core/dbupgrade.py \
    --ignore=infogami/infobase/_json.py \
    --ignore=infogami/infobase/bulkupload.py \
    --ignore=infogami/infobase/tests/test_account.py \
    --ignore=infogami/infobase/tests/test_client.py \
    --ignore=infogami/infobase/tests/test_infobase.py \
    --ignore=infogami/infobase/tests/test_read.py \
    --ignore=infogami/infobase/tests/test_save.py \
    --ignore=infogami/infobase/tests/test_seq.py \
    --ignore=infogami/infobase/tests/test_store.py \
    --ignore=infogami/infobase/tests/test_writequery.py \
    --ignore=infogami/plugins/i18n/code.py \
    --ignore=infogami/plugins/links/db.py \
    --ignore=infogami/plugins/pages/code.py \
    --ignore=infogami/plugins/review/code.py \
    --ignore=infogami/plugins/review/db.py \
    --ignore=infogami/plugins/wikitemplates/code.py  \
    --ignore=migration/migrate-0.4-0.5.py \
    --ignore=test/bug_239238.py \
    --ignore=test/test_dbstore.py

# ALL fail on both Python 2 and Python 3
# infogami/core/dbupgrade.py \                  # Fails on Py2 & Py3... import tdb
# infogami/infobase/_json.py \                  # Fails on Py2 & Py3
# infogami/infobase/bulkupload.py \             # Fails on Py2 & Py3... import TYPES
# infogami/infobase/tests/test_account.py \     # Fails on Py2 & Py3
# infogami/infobase/tests/test_client.py \      # Fails on Py2 & Py3
# infogami/infobase/tests/test_infobase.py \    # Fails on Py2 & Py3
# infogami/infobase/tests/test_read.py \        # Fails on Py2 & Py3
# infogami/infobase/tests/test_save.py \        # Fails on Py2 & Py3
# infogami/infobase/tests/test_seq.py \         # Fails on Py2 & Py3
# infogami/infobase/tests/test_store.py \       # Fails on Py2 & Py3
# infogami/infobase/tests/test_writequery.py \  # Fails on Py2 & Py3
# infogami/plugins/i18n/code.py \               # Fails on Py2 & Py3... AttributeError: 'db_parameters'
# infogami/plugins/links/db.py \                # Fails on Py2 & Py3... import tdb
# infogami/plugins/pages/code.py \              # Fails on Py2 & Py3... import tdb
# infogami/plugins/review/code.py \             # Fails on Py2 & Py3... import pickdb
# infogami/plugins/review/db.py \               # Fails on Py2 & Py3... import pickdb
# infogami/plugins/wikitemplates/code.py  \     # Fails on Py2 & Py3... HTTPError: 500 Internal Server Error
# migration/migrate-0.4-0.5.py \                # Fails on Py2 & Py3
# test/bug_239238.py \                          # Fails on Py2 & Py3... AttributeError: 'db_parameters'
# test/test_dbstore.py                          # Fails on Py2 & Py3... psycopg2 OperationalError
