import os
from pathlib import Path
from billsim.pymodels import BillPath

TEST_INDEX_SECTIONS = 'billsim_test'
TEST_INDEX_BILL_FULL = 'billsim_bill_full_test'

# This is set low for the moreLikeThis queries
# because the tfidf scores are limited by a small corpus
TEST_MIN_SCORE = 10

TEST_DIR = Path(__file__).resolve(strict=True).parent
SAMPLE_BILL_PATH = BillPath(
    billnumber_version='117hr200ih',
    fileName='BILLS-117hr200ih.xml',
    filePath=os.path.join(
        TEST_DIR, 'samples/data/congress/117/bills/hr200/BILLS-117hr200ih.xml'))

SAMPLE_BILL_PATH_117HR2001 = BillPath(
    billnumber_version='117hr2001ih',
    fileName='BILLS-117hr2001ih.xml',
    filePath=os.path.join(
        TEST_DIR,
        'samples/data/congress/117/bills/hr2001/BILLS-117hr2001ih.xml'))

SAMPLE_QUERY_TEXT = """
2. National Intersection and Interchange Safety Construction Program (a) Establishment 
Not later than 180 days after the date of enactment of this Act, the Secretary of Transportation shall establish a national intersection and interchange safety construction program (in this section referred to as the Program) to assist safety improvements for high-risk intersections and interchanges.(b) Grant authority(1) In general
In carrying out the Program, the Secretary may make a grant to a covered entity in accordance with this section.(2) Competitive basisThe Secretary shall award grants under the Program on a competitive basis.
(c) Project requirementsThe Secretary may only make a grant under the Program to assist a project that—(1)is eligible for funding under title 23, United States Code; and(2)will improve the safety of an intersection or interchange that is—(A) on the National Highway System;(B) used by an average of 50,000 vehicles a day; and
(C) in immediate need of improvement with respect to safety.(d) ApplicationsTo be eligible for a grant under the Program, a covered entity shall submit to the Secretary an application in such form, at such time, and containing such information as the Secretary determines is appropriate.(e) LimitationThe aggregate amount provided to a covered entity in a fiscal year through grants under the Program may not exceed 5 percent of the amount made available for all grants under the Program in that fiscal year.(f) Congressional reviewAt least 90 days before establishing the Program under subsection (a), the Secretary shall submit to Congress a report detailing the selection process the Secretary shall use in making grants under the Program.(g) Covered entity definedIn this section, the term covered entity means each of the following:(1) A State government entity.(2) A local government entity.(3) A territory of the United States.(4) A tribal government.(5) A metropolitan planning organization.
(6) Any entity composed of 2 or more entities described in paragraphs (1) through (5)(h) Authorization of appropriations(1) In general
There is authorized to be appropriated out of the Highway Trust Fund (other than the Mass Transit Account) to carry out the Program $250,000,000 each fiscal year.(2) Applicability of title 23, United States CodeFunds authorized to be appropriated by paragraph (1) shall—(A) be available for obligation in the same manner as if those funds were apportioned under chapter 1 of title 23, United States Code, except that the Federal share of the cost of a project or activity carried out using those funds shall be 80 percent; and(B) remain available until expended and not be transferable.
"""
