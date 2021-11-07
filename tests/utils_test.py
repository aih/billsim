#!/usr/bin/env python3

import os
from pathlib import Path
from billsim.constants import CONGRESS_DATA_PATH
from billsim.pymodels import BillPath

BASE_DIR = Path(__file__).resolve(strict=True).parent

CONGRESS_DATA_PATH_TEST = os.path.join(BASE_DIR, 'samples', 'congress', 'data')

def test_walkBillDirs(rootDir = CONGRESS_DATA_PATH_TEST):
    from billsim.utils import walkBillDirs
    billDirs = walkBillDirs(rootDir=rootDir)
    assert len(billDirs) == 27
    assert billDirs[2].billnumber_version == "116hr2005ih"
    assert billDirs[2].fileName == "BILLS-116hr2005ih.xml"