import os
from pathlib import Path
from billsim.pymodels import BillPath

TEST_INDEX_SECTIONS = 'billsim_test'
TEST_INDEX_BILL_FULL = 'billsim_bill_full_test'

TEST_DIR = Path(__file__).resolve(strict=True).parent
SAMPLE_BILL_PATH = BillPath(
    billnumber_version='117hr200ih',
    fileName='BILLS-117hr200ih.xml',
    filePath=os.path.join(
        TEST_DIR, 'samples/data/congress/117/bills/hr200/BILLS-117hr200ih.xml'))
