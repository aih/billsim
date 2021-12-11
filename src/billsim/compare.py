import subprocess
import json
from billsim import pymodels
from billsim.constants import COMPAREMATRIX_GO_CMD
from billsim.utils import billNumberVersionToBillPath


def getComparisonMatrix(billnumbers: list[str]) -> list[list]:
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
