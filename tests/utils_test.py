#!/usr/bin/env python3

import os
from lxml import etree
from pathlib import Path
from billsim.constants import CONGRESS_DATA_PATH
from billsim.pymodels import BillPath

BASE_DIR = Path(__file__).resolve(strict=True).parent

CONGRESS_PATH_TEST = os.path.join(BASE_DIR, 'samples', 'congress')
CONGRESS_DATA_PATH_TEST = os.path.join(CONGRESS_PATH_TEST, 'data')


def test_deep_get():
    from billsim.utils import deep_get
    d = {
        'meta': {
            'status': 'OK',
            'status_code': 200,
            'messages': ['first', 'second', 'third']
        },
        'data': {
            'a': 1,
            'b': 2,
            'c': 3
        }
    }
    assert (deep_get(d, ['meta', 'status']) == 'OK')
    assert (deep_get(d, ['meta', 'status_code']) == 200)
    assert (deep_get(d, ['meta', 'messages', 0]) == 'first')
    assert (deep_get(d, ['garbage', 'status_code']) == None)
    assert (deep_get(d, ['meta', 'garbage'], default='-') == '-')


section_data = """<section id="H93C64B1CB03F40CD8666BB62DA698757">
		<enum>2.</enum>
		<header>National Intersection and Interchange Safety Construction Program</header>
        </section>"""
section = etree.fromstring(section_data, parser=etree.XMLParser())


def test_getId():
    from billsim.utils import getId
    id = getId(section)
    assert id == "H93C64B1CB03F40CD8666BB62DA698757"


def test_getEnum():
    from billsim.utils import getEnum
    enum = getEnum(section)
    assert enum == "2."


# Tests both getHeader and getText, which it depends on
def test_getHeader():
    from billsim.utils import getHeader
    header = getHeader(section)
    assert header == "National Intersection and Interchange Safety Construction Program"


def test_billNumberVersionToBillPath():
    from billsim.utils import billNumberVersionToBillPath
    billPath = billNumberVersionToBillPath("116hr2005ih")
    assert billPath.billnumber_version == "116hr2005ih"
    assert billPath.fileName == "BILLS-116hr2005ih.xml"
    assert billPath.filePath == os.path.join(CONGRESS_DATA_PATH_TEST,
                                             "BILLS-116hr2005ih.xml")


def test_walkBillDirs(rootDir=CONGRESS_DATA_PATH_TEST):
    from billsim.utils import walkBillDirs
    billDirs = walkBillDirs(rootDir=rootDir)
    assert len(billDirs) >= 27
    assert billDirs[2].billnumber_version == "116hr2005ih"
    assert billDirs[2].fileName == "BILLS-116hr2005ih.xml"


def test_getBillXmlPaths(congressDir=CONGRESS_PATH_TEST):
    from billsim.utils import getBillXmlPaths
    billDirs = getBillXmlPaths(congressDir=congressDir)
    assert len(billDirs) >= 27
    assert billDirs[2].billnumber_version == "116hr2005ih"
    assert billDirs[2].fileName == "BILLS-116hr2005ih.xml"