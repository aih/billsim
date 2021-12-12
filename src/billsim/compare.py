import subprocess
import json
from billsim import pymodels
from billsim.constants import COMPAREMATRIX_GO_CMD
from billsim.utils import billNumberVersionToBillPath
from billsim.bill_similarity import getSimilarBillSections, getBillToBill
from billsim.utils_db import save_bill_to_bill, save_bill_to_bill_sections
from billsim.pymodels import BillToBillModel


def getCompareMatrix(billnumbers: list[str]) -> list[list]:
    billPaths = [
        billNumberVersionToBillPath(billnumber).filePath
        for billnumber in billnumbers
    ]
    billPathsString = ",".join(billPaths)
    result = subprocess.run(
        [COMPAREMATRIX_GO_CMD, '-abspaths', billPathsString],
        capture_output=True,
        text=True)
    comparematrix = json.loads(result.stdout.split(':compareMatrix:')[1])
    # matrix of the form '[[{1 identical} {0.63 incorporates}] [{0.79 incorporated by} {1 identical}]]'
    return comparematrix


def processSimilarBills(billnumber_versions: list[str]) -> None:
    # TODO: test that billnumber_versions is a list of billnumbers
    for billnumber_version in billnumber_versions:
        s = getSimilarBillSections(billnumber_version)
        b2b = getBillToBill(s)
        for bill in b2b:
            save_bill_to_bill(b2b[bill])
            save_bill_to_bill_sections(
                b2b[bill]
            )    # This should save the individual sections and the sections to section mapping

        # Get similarity scores for bill-to-bill
        # Calls comparematrix from bills (Golang);
        similar_bills = b2b.keys()
        c = getCompareMatrix(list(similar_bills))
        for row in c:
            for column in row:
                compare_bill, compare_bill_to = column['ComparedDocs'].split(
                    '-')
                if compare_bill and compare_bill_to:
                    b2bModel = BillToBillModel(
                        billnumber_version=compare_bill,
                        billnumber_version_to=compare_bill_to,
                        score=column['Score'],
                        score_to=column['ScoreOther'],
                        reasons=[column['Explanation']])
                    save_bill_to_bill(b2bModel)
