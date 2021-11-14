import os
from pathlib import Path
import pytest
from billsim.elastic_load import es
from billsim.pymodels import BillPath
from tests import constants_test


def es_service_available() -> bool:
    service_available = es.ping()
    if not service_available:
        print('Elasticsearch service not available')
    return service_available


@pytest.mark.skipif(not es_service_available(),
                    reason="Elasticsearch service not available")
@pytest.mark.order(1)
def test_createIndex():
    from billsim.elastic_load import createIndex
    createIndex(index=constants_test.TEST_INDEX_SECTIONS, delete=True)
    assert (es.indices.exists(index=constants_test.TEST_INDEX_SECTIONS))


@pytest.mark.skipif(not es_service_available(),
                    reason="Elasticsearch service not available")
@pytest.mark.order(2)
def test_indexBill():
    from billsim.elastic_load import indexBill
    billPath = constants_test.SAMPLE_BILL_PATH
    r = indexBill(billPath=billPath,
                  index_types={
                      'sections': constants_test.TEST_INDEX_SECTIONS,
                      'bill_full': constants_test.TEST_INDEX_BILL_FULL
                  })
    assert r is not None
    assert r.success
