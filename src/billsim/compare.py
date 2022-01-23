from re import T
import sys
import logging
import subprocess
import json
import argparse
import random
from typing import List
from billsim import pymodels
from billsim.constants import COMPAREMATRIX_GO_CMD, TIMEOUT_SECONDS
from billsim.utils import billNumberVersionToBillPath, getBillXmlPaths, getBillnumberversionParts
from billsim.bill_similarity import getSimilarBillSections, getBillToBill
from billsim.utils_db import save_bill_to_bill, save_bill_to_bill_sections
from billsim.pymodels import BillToBillModel

logging.basicConfig(filename='compare.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

# See https://stackoverflow.com/a/63546765/628748
# and https://stackoverflow.com/a/66515961/628748
from contextlib import contextmanager
import signal
import time


@contextmanager
def timeout(duration):

    def timeout_handler(signum, frame):
        raise Exception(f'block timed out after {duration} seconds')

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    yield
    signal.alarm(0)


def getCompareMatrix(billnumbers: list[str]) -> list[list]:
    billPaths = [
        billNumberVersionToBillPath(billnumber).filePath
        for billnumber in billnumbers
    ]
    billPathsString = ",".join(billPaths)
    logger.debug(billPathsString)
    result = subprocess.run(
        [COMPAREMATRIX_GO_CMD, '-abspaths', billPathsString],
        capture_output=True,
        text=True)
    logger.info(result.stdout)
    comparematrixContents = result.stdout.split(':compareMatrix:')
    if len(comparematrixContents) == 3 and comparematrixContents[1] != '':
        comparematrix = json.loads(comparematrixContents[1])
    else:
        comparematrix = json.loads('{}')
    # matrix of the form '[[{1 identical} {0.63 incorporates}] [{0.79 incorporated by} {1 identical}]]'
    return comparematrix


def scoreBillToBills(billnumber_version: str,
                     similar_bills: list[str],
                     timeout_secs: int = TIMEOUT_SECONDS) -> list[str]:
    # Get similarity scores for bill-to-bill
    # Calls comparematrix from bills (Golang);
    # Saves bill-to-bill with scores for bill + similar bills
    # This function can be expanded, or replaced to use another scoring method (e.g. vector similarity)
    try:
        with timeout(timeout_secs):
            c = getCompareMatrix(similar_bills)
    except Exception as e:
        logger.error(
            f'Timed out getting Compare Matrix for bill {billnumber_version}: {e}'
        )
        return []
    try:
        with timeout(timeout_secs):
            for row in c:
                for column in row:
                    compare_bill, compare_bill_to = column[
                        'ComparedDocs'].split('-')

                    # Only stores the first row of the matrix
                    # Where the 'from' bill is the bill to compare
                    if compare_bill and compare_bill_to and compare_bill == billnumber_version:
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
    except Exception as e:
        logger.error(
            f'Timed out processing bill-to-bill for bill {billnumber_version}: {e}'
        )
        return []
    return similar_bills


def processSimilarBills(billnumber_version: str,
                        timeout_secs: int = TIMEOUT_SECONDS,
                        add_similarity_scores=False) -> list[str]:
    logger.info(
        f'Processing similar bills for bill {billnumber_version} with timeout of {timeout_secs} seconds'
    )
    try:
        getBillnumberversionParts(billnumber_version)
    except ValueError:
        logger.error(
            f'billnumber_version {billnumber_version} is not a valid billnumber_version'
        )
        return []

    try:
        s = getSimilarBillSections(billnumber_version)
        b2b = getBillToBill(s)
    except Exception as e:
        logger.error(
            f'Error getting similar bill sections for {billnumber_version}')
        return []
    for bill in b2b:
        save_bill_to_bill(b2b[bill])
        save_bill_to_bill_sections(b2b[bill])
    similar_bills = list(b2b.keys())

    if add_similarity_scores:
        similar_bills = scoreBillToBills(billnumber_version,
                                         similar_bills=similar_bills,
                                         timeout_secs=timeout_secs)
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
