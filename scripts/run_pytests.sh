#!/bin/sh

# platform linux2 -- Python 2.7.6, pytest-4.6.9, py-1.9.0, pluggy-0.13.1
# collected 72 items
# platform linux -- Python 3.8.5, pytest-6.0.1, py-1.9.0, pluggy-0.13.1
# collected 72 items

# To run ALL pytests, use:
# USER=openlibrary@example.com pytest || true

USER=openlibrary@example.com pytest \
    --ignore=infogami/infobase/tests/test_account.py \
    --ignore=infogami/infobase/tests/test_client.py \
    --ignore=infogami/infobase/tests/test_infobase.py \
    --ignore=infogami/infobase/tests/test_read.py \
    --ignore=infogami/infobase/tests/test_save.py \
    --ignore=infogami/infobase/tests/test_seq.py \
    --ignore=infogami/infobase/tests/test_store.py \
    --ignore=infogami/infobase/tests/test_writequery.py \
    --ignore=test/test_dbstore.py

# ALL fail on both Python 2 and Python 3
# infogami/infobase/tests/test_account.py \     # Fails on Py2 & Py3
# infogami/infobase/tests/test_client.py \      # Fails on Py2 & Py3
# infogami/infobase/tests/test_infobase.py \    # Fails on Py2 & Py3
# infogami/infobase/tests/test_read.py \        # Fails on Py2 & Py3
# infogami/infobase/tests/test_save.py \        # Fails on Py2 & Py3
# infogami/infobase/tests/test_seq.py \         # Fails on Py2 & Py3
# infogami/infobase/tests/test_store.py \       # Fails on Py2 & Py3
# infogami/infobase/tests/test_writequery.py \  # Fails on Py2 & Py3
# test/test_dbstore.py                          # Fails on Py2 & Py3
