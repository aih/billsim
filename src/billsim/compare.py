import sys
import time
import logging
import subprocess
import json
import argparse
import random
from billsim import pymodels
from billsim.constants import COMPAREMATRIX_GO_CMD
from billsim.utils import billNumberVersionToBillPath, getBillXmlPaths, getBillnumberversionParts
from billsim.bill_similarity import getSimilarBillSections, getBillToBill
from billsim.utils_db import save_bill_to_bill, save_bill_to_bill_sections
from billsim.pymodels import BillToBillModel

logging.basicConfig(filename='compare.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


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


def processSimilarBills(billnumber_version: str) -> list[str]:
    logger.info(f'Processing similar bills for bill {billnumber_version}')
    try:
        getBillnumberversionParts(billnumber_version)
    except ValueError:
        logger.error(
            f'billnumber_version {billnumber_version} is not a valid billnumber_version'
        )
        return []

    s = getSimilarBillSections(billnumber_version)
    b2b = getBillToBill(s)
    for bill in b2b:
        save_bill_to_bill(b2b[bill])
        save_bill_to_bill_sections(b2b[bill])

    # Get similarity scores for bill-to-bill
    # Calls comparematrix from bills (Golang);
    similar_bills = list(b2b.keys())
    c = getCompareMatrix(similar_bills)
    for row in c:
        for column in row:
            compare_bill, compare_bill_to = column['ComparedDocs'].split('-')
            if compare_bill and compare_bill_to:
                b2bModel = BillToBillModel(
                    billnumber_version=compare_bill,
                    billnumber_version_to=compare_bill_to,
                    score=column['Score'],
                    score_to=column['ScoreOther'],
                    reasons=[
                        reason.strip()
                        for reason in column['Explanation'].split(', ')
                    ])
                save_bill_to_bill(b2bModel)
    return similar_bills


def compareBills(maxBills: int = -1):
    start_time = time.time()
    billPaths = getBillXmlPaths()
    if maxBills > 0:
        billPaths = random.sample(billPaths, maxBills)
        logger.info(f'Sampled {len(billPaths)} bills to process')
    else:
        maxBills = len(billPaths)
    for i, billPath in enumerate(billPaths):
        if i % 100 == 0:
            logger.info(f'Processed {i} bills')
        try:
            similar_bills = processSimilarBills(billPath.billnumber_version)
            logger.debug(
                f'{billPath.billnumber_version} has {len(similar_bills)} similar bills: {similar_bills}'
            )
        except Exception as e:
            logger.error(
                f'Error processing similarbills for bill {billPath.billnumber_version}: {e}'
            )
    end_time = time.time()
    logger.info("It took {0} seconds to process {1} bills.".format(
        end_time - start_time, maxBills))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Get similarity scores for bills.')
    parser.add_argument('max',
                        metavar='m',
                        type=int,
                        help='max number of bills to compare')

    args = parser.parse_args()
    compareBills(maxBills=args.max)
