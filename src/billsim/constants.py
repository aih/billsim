#!/usr/bin/env python3

import os
import re
import datetime
from copy import deepcopy
import pkgutil
import json

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PATHTYPE_DEFAULT = os.getenv('PATHTYPE_DEFAULT', default='congressdotgov')

PATH_TO_DATA_DIR = os.getenv(
    'PATH_TO_DATA_DIR',
    os.path.join('/', *"/usr/local/share/billsim/public/data".split('/')))

PATH_TO_CONGRESSDATA_DIR = os.getenv('PATH_TO_CONGRESS_DATA_DIR',
                                     default=os.path.join(
                                         PATH_TO_DATA_DIR, 'congress'))

BASE_DIR = Path(__file__).resolve(strict=True).parent

PATH_BILLSECTIONS_JSON = os.path.join(BASE_DIR, 'es/billsections_mapping.json')
PATH_BILL_FULL_JSON = os.path.join(BASE_DIR, 'es/bill_full_mapping.json')

# Names of elasticsearch indices
INDEX_SECTIONS = os.getenv('INDEX_SECTIONS', default='billsim')
INDEX_BILL_FULL = os.getenv('INDEX_BILL_FULL', default='bill_full')

SCORE_MODE_AVG = 'avg'
SCORE_MODE_MAX = 'max'
SCORE_MODE_SUM = 'sum'

# largest number of results for a query of sections
MAX_BILLS_SECTION = int(os.getenv('MAX_BILLS_SECTIONS', default=100))

BILLMETA_GO_CMD = 'billmeta'
ESQUERY_GO_CMD = 'esquery'
COMPAREMATRIX_GO_CMD = 'comparematrix'

RESULTS_DEFAULT = 20
MIN_SCORE_DEFAULT = 25

try:
    BILLSECTION_MAPPING = json.loads(
        pkgutil.get_data(__name__, PATH_BILLSECTIONS_JSON).decode("utf-8"))
    BILL_FULL_MAPPING = json.loads(
        pkgutil.get_data(__name__, PATH_BILL_FULL_JSON).decode("utf-8"))
except Exception as err:

    with open(PATH_BILLSECTIONS_JSON, 'r') as f:
        BILLSECTION_MAPPING = json.load(f)

    with open(PATH_BILL_FULL_JSON, 'r') as f:
        BILL_FULL_MAPPING = json.load(f)

#PATH_TO_RELATEDBILLS = '../relatedBills.json'
SAVE_ON_COUNT = 1000

BILL_ID_REGEX = r'[a-z]+[1-9][0-9]*-[1-9][0-9]+'
BILL_NUMBER_PART_REGEX = r'(?P<congress>[1-9][0-9]*)(?P<stage>[a-z]+)(?P<billnumber>[0-9]+)(?P<version>[a-z]+)?'
BILL_NUMBER_PART_REGEX_COMPILED = re.compile(BILL_NUMBER_PART_REGEX)
BILL_NUMBER_REGEX = BILL_NUMBER_PART_REGEX + '$'
BILL_NUMBER_REGEX_COMPILED = re.compile(BILL_NUMBER_REGEX)
BILL_DIR_REGEX = r'.*?([1-9][0-9]*)\/bills\/[a-z]+\/([a-z]+)([0-9]+)$'
BILL_DIR_REGEX_COMPILED = re.compile(BILL_DIR_REGEX)
BILL_DIR_REGEX_CDG = r'.*?([1-9][0-9]*)\/bills\/([a-z]+)([0-9]+)$'
BILL_DIR_REGEX_CDG_COMPILED = re.compile(BILL_DIR_REGEX_CDG)

# /data/congress/117/bills/sconres/sconres2
US_CONGRESS_VERSION_PATH_REGEX_COMPILED = re.compile(
    r'\/(?P<congress>[1-9][0-9]*)\/(?P<doctype>[a-z]+)\/(?P<stage>[a-z]{1,8})\/(?P<billnumber>[a-z]{1,8}[1-9][0-9]*)\/?(text-versions\/)?(?P<version>[a-z]+)'
)
US_CONGRESS_PATH_REGEX_COMPILED = re.compile(
    r'\/(?P<congress>[1-9][0-9]*)\/(?P<doctype>[a-z]+)\/(?P<stage>[a-z]{1,8})\/(?P<billnumber>[a-z]{1,8}[1-9][0-9]*)\/?(text-versions\/)?(?P<version>[a-z]+)?'
)
USCONGRESS_XML_FILE = 'document.xml'


# CDG = congress.gov
def billNumberVersionFromPath_CDG(path: str):
    match = BILL_NUMBER_PART_REGEX_COMPILED.search(path)
    if match:
        return match.group(0)
    else:
        return ''


def billNumberVersionToPath_CDG(billnumber_version: str):
    match = BILL_NUMBER_PART_REGEX_COMPILED.search(billnumber_version)
    if match:
        return '{congress}/bills/{stage}{billnumber}/BILLS-{congress}{stage}{billnumber}{version}.xml'.format(
            **match.groupdict())
    else:
        return ''


# data/117/bills/hr200/
def isFileParent_CDG(path: str):
    match = BILL_DIR_REGEX_CDG_COMPILED.search(path)
    if match:
        return True
    else:
        return False


def billNumberVersionFromPath_USCONGRESS(path: str):
    match = US_CONGRESS_PATH_REGEX_COMPILED.search(path)
    if match:
        return '{congress}{stage}{billnumber}{version}'.format(
            match.groupdict())
    else:
        return ''


def billNumberVersionToPath_USCONGRESS(billnumber_version: str):
    match = BILL_NUMBER_PART_REGEX_COMPILED.search(billnumber_version)
    if match:
        return '{congress}/bills/{stage}/{stage}{billnumber}/text-versions/{version}/document.xml'.format(
            **match.groupdict())
    else:
        return ''


# congress/data/117/bills/sconres/sconres2/text-versions/ih
def isFileParent_USCONGRESS(path: str):
    match = US_CONGRESS_VERSION_PATH_REGEX_COMPILED.search(path)
    if match:
        return True
    else:
        return False


CONGRESS_DIRS = {
    "congressdotgov": {
        "samplePath":
            "data/congress/117/bills/hr200/BILLS-117hr200ih.xml",
        "billXMLFilenameRegex":
            r'BILLS-' + BILL_NUMBER_PART_REGEX + r'\.xml',
        "pathToBillnumberVersion":
            billNumberVersionFromPath_CDG,
        "billNumberVersionToPath":
            billNumberVersionToPath_CDG,
        "isFileParent":
            isFileParent_CDG,
        "fileMatch":
            lambda x: re.compile(r'BILLS-' + BILL_NUMBER_PART_REGEX + r'\.xml').
            match(x) is not None
    },
    "unitedstates": {
        "samplePath":
            f'data/congress/117/bills/sconres/sconres2/text-versions/ih/{USCONGRESS_XML_FILE}',
        "billXMLFilenameRegex":
            r'' + USCONGRESS_XML_FILE,
        "pathToBillnumberVersion":
            billNumberVersionFromPath_USCONGRESS,
        "billNumberVersionToPath":
            billNumberVersionToPath_USCONGRESS,
        "isFileParent":
            isFileParent_USCONGRESS,
        "fileMatch":
            lambda x: re.compile(r'' + USCONGRESS_XML_FILE).match(x) is not None
    }
}

PATHTYPE_OBJ = CONGRESS_DIRS[PATHTYPE_DEFAULT]

CURRENT_CONGRESSIONAL_YEAR = datetime.date.today(
).year if datetime.date.today() > datetime.date(
    datetime.date.today().year, 1, 3) else (datetime.date.today().year - 1)
START_CONGRESS = 110    # Earliest Congress with data in our database
CURRENT_CONGRESS, cs_temp = divmod(
    round(((datetime.date(CURRENT_CONGRESSIONAL_YEAR, 1, 3) -
            datetime.date(1788, 1, 3)).days) / 365) + 1, 2)
CURRENT_SESSION = cs_temp + 1

BILL_TYPES = {
    'ih': 'IH-Introduced (House)',
    'as': 'AS-Amendment (Senate)',
    'ash': 'ASH-Additional Sponsors (House)',
    'ath': 'ATH-Agreed to (House)',
    'ats': 'ATS-Agreed to (Senate)',
    'cdh': 'CDH-Committee Discharged (House)',
    'cds': 'CDS-Committee Discharged (Senate)',
    'cph': 'CPH-Considered and Passed (House)',
    'cps': 'CPS-Considered and Passed (Senate)',
    'eah': 'EAH-Engrossed Amendment (House)',
    'eas': 'EAS-Engrossed Amendment (Senate)',
    'eh': 'EH-Engrossed (House)',
    'es': 'ES-Engrossed (Senate)',
    'enr': 'ENR-Enrolled',
    'eph': 'EPH-Engrossed and Deemed Passed by House',
    'fah': 'FAH-Failed Amendment (House)',
    'fph': 'FPH-Failed Passage (House)',
    'fps': 'FPS-Failed Passage (Senate)',
    'hdh': 'HDH-Held at Desk (House)',
    'hds': 'HDS-Held at Desk (Senate)',
    'iph': 'IPH-Indefinitely Postponed (House)',
    'ips': 'IPS-Indefinitely Postponed (Senate)',
    'is': 'IS-Introduced (Senate)',
    'lth': 'LTH-Laid on Table (House)',
    'lts': 'LTS-Laid on Table (Senate)',
    'oph': 'OPH-Ordered to be Printed (House)',
    'ops': 'OPS-Ordered to be Printed (Senate)',
    'pap': 'PAP-Printed as Passed',
    'pav': 'PAV-Previous Action Vitiated',
    'pch': 'PCH-Placed on Calendar (House)',
    'pcs': 'PCS-Placed on Calendar (Senate)',
    'pp': 'PP-Public Print',
    'pwah': 'PWAH-Ordered to be Printed with House Amendment',
    'rah': 'RAH-Referred with Amendments (House)',
    'ras': 'RAS-Referred with Amendments (Senate)',
    'rch': 'RCH-Reference Change (House)',
    'rcs': 'RCS-Reference Change (Senate)',
    'rdh': 'RDH-Received in (House)',
    'rds': 'RDS-Received in (Senate)',
    'reah': 'REAH-Re-engrossed Amendment (House)',
    'renr': 'RENR-Re-enrolled Bill',
    'res': 'RES-Re-engrossed Amendment (Senate)',
    'rfh': 'RFH-Referred in (House)',
    'rfs': 'RFS-Referred in (Senate)',
    'rh': 'RH-Reported in (House)',
    'rih': 'RIH-Referral Instructions (House)',
    'ris': 'RIS-Referral Instructions (Senate)',
    'rs': 'RS-Reported in (Senate)',
    'rth': 'RTH-Referred to Committee (House)',
    'rts': 'RTS-Referred to Committee (Senate)',
    'sas': 'SAS-Additional Sponsors (Senate)',
    'sc': 'SC-Sponsor Change'
}

# Returns all documents (up to "size")
SAMPLE_MATCH_ALL_QUERY = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "query": {
        "match_all": {}
    }
}

SAMPLE_QUERY = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "query": {
        "match": {
            "headers": {
                "query": "date"
            }
        }
    }
}

SAMPLE_QUERY_W_CONGRESS = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "query": {
        "bool": {
            "must": [{
                "match": {
                    "headers": {
                        "query": "date"
                    }
                }
            }],
            "filter": [{
                "term": {
                    "congress": "115"
                }
            }]
        }
    }
}

SAMPLE_QUERY_NESTED = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "query": {
        "nested": {
            "path": "sections",
            "query": {
                "bool": {
                    "must": [{
                        "match": {
                            "sections.section_header": "title"
                        }
                    }]
                }
            },
            "inner_hits": {
                "highlight": {
                    "fields": {
                        "sections.section_header": {}
                    }
                }
            }
        }
    }
}

# more like this query (working)
SAMPLE_QUERY_MLT_HEADERS = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "query": {
        "more_like_this": {
            "fields": ["headers"],
            "like": "Dependent care credit improvements",
            "min_term_freq": 1,
            "max_query_terms": 10,
            "min_doc_freq": 1
        }
    }
}

reporting_requirement = """
Not later than 5 years after the date of enactment of this Act, the administering Secretaries, acting jointly, shall report to the appropriate committees of Congress on the progress in the reduction of food waste that can be attributed to the standardization of food date labeling and consumer education required by this Act and the amendments made by this Act
"""

quality_date_guidance = """
The Commissioner of Food and Drugs and the Secretary of Agriculture shall establish guidance for food labelers on how to determine quality dates and safety dates for food products.
"""

forestry_programs = """
SEC. 5. MEMORANDUM OF UNDERSTANDING TO COORDINATE URBAN FORESTRY PROGRAMS.

Not later than 120 days after the date of the enactment of this Act, the Secretary of Agriculture shall enter into a memorandum of understanding with the Secretaries of Health and Human Services, Housing and Urban Development, Interior, Labor, and Transportation and the Administrator of the Environmental Protection Agency to—

(1) identify strategies to increase equitable access to urban forests through existing programs and authorities;

(2) coordinate existing urban forestry programs;

(3) conduct research on the benefits of urban forests for air quality, heat island mitigation, energy burden reduction, and enhanced shading for heat-resilient housing and active transit; and

(4) conduct research on improving coordination between the agencies to address insects, disease, and non-native invasive species in urban and community areas.
"""

misc_civil_rights = """
SEC. 9. MISCELLANEOUS. Title XI of the Civil Rights Act of 1964 is amended— 
(1) by redesignating sections 1101 through 1104 (42 U.S.C. 2000h et seq.) and sections 1105 and 1106 (42 U.S.C. 2000h–5, 2000h–6) as sections 1102 through 1105 and sections 1108 and 110
"""

# 117hr4973
beef_label = """
SEC. 2. PRODUCT OF U.S.A. LABEL FOR BEEF.

Section 7 of the Federal Meat Inspection Act (21 U.S.C. 607) is amended by adding at the end the following:


“(g) Product Of The United States Label For Beef.—

“(1) IN GENERAL.—Subject to paragraph (2), the label of meat of cattle or a meat food product of cattle may bear the phrase ‘Product of U.S.A.’, or any substantially similar word or phrase, only if the meat or meat food product is exclusively derived from 1 or more cattle exclusively born, raised, and slaughtered in the United States.

“(2) INAPPLICABILITY.—Paragraph (1) shall not apply to meat of cattle or a meat food product of cattle that is intended and offered for export to a foreign country.”.
"""


def getQueryText(text_path: str = ''):
    with open(text_path, 'r') as f:
        queryText = f.read()
    if not queryText:
        queryText = ''
    return queryText


# more like this query (working)
# Note that we can change the "nested.score_mode" to "max"
# to give the overall doc score the highest score of the nested docs (sections)
SAMPLE_QUERY_NESTED_MLT = {
    "size": RESULTS_DEFAULT,
    "min_score": MIN_SCORE_DEFAULT,
    "_source": ["id", "congress", "session"],
    "query": {
        "nested": {
            "score_mode": "max",
            "path": "sections",
            "query": {
                "more_like_this": {
                    "fields": ["sections.section_text"],
                    "like": forestry_programs,
                    "min_term_freq": 2,
                    "max_query_terms": 30,
                    "min_doc_freq": 2
                }
            },
            "inner_hits": {
                "_source": [
                    "sections.section_id", "sections.section_number",
                    "sections.section_header", "sections.section_length"
                ],
                "highlight": {
                    "fields": {
                        "sections.section_text": {}
                    }
                }
            }
        }
    }
}


def makeMLTQuery(queryText: str,
                 queryTextPath: str = '',
                 min_score: int = MIN_SCORE_DEFAULT,
                 score_mode: str = SCORE_MODE_AVG):
    if queryTextPath and not queryText:
        try:
            queryText = getQueryText(queryTextPath)
        except Exception as err:
            raise Exception('Error getting text from path: {0}'.format(err))

    newQuery = deepcopy(SAMPLE_QUERY_NESTED_MLT)
    newQuery['min_score'] = min_score
    newQuery['query']['nested']['query']['more_like_this']['like'] = queryText
    newQuery['query']['nested']['score_mode'] = score_mode
    return newQuery
