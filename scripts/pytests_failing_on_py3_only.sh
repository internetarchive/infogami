#!/usr/bin/env bash

PASSING_TESTS=(
    infogami/core/code.py
    infogami/infobase/_dbstore/indexer.py
    infogami/infobase/common.py
    infogami/infobase/tests/test_doctests.py
    infogami/utils/app.py
    infogami/utils/view.py
    tests/__init__.py
    test/test_doctests.py
)

FAILING_TESTS=(
    infogami/infobase/tests/__init__.py
    infogami/infobase/tests/test_account.py
    infogami/infobase/tests/test_client.py
    infogami/infobase/tests/test_infobase.py
    infogami/infobase/tests/test_read.py
    infogami/infobase/tests/test_save.py
    infogami/infobase/tests/test_seq.py
    infogami/infobase/tests/test_store.py
    infogami/infobase/tests/test_writequery.py
    test/test_dbstore.py
    tests/test_doctests.py
)

for FILEPATH in "${FAILING_TESTS[@]}"; do
    echo "<<< $FILEPATH >>>"
    pytest "$FILEPATH"
    # See TODO in test/test_dbstore.py
    if [ "$FILEPATH" != "test/test_dbstore.py" ]; then
        pytest --doctest-modules "$FILEPATH";
    fi
done
