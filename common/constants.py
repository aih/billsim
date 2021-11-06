import os
import re
import datetime
from copy import deepcopy
import pkgutil
import json

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

CONGRESS_DATA_PATH = os.path.join(BASE_DIR, 'congress', 'data')
BILLS_JSON_PATH = os.path.join(BASE_DIR, 'json_data') 

PATH_BILLSECTIONS_JSON = os.path.join(
    BASE_DIR, 'elasticsearch/billsections_mapping.json')
PATH_BILL_FULL_JSON = os.path.join(
    BASE_DIR, 'elasticsearch/bill_full_mapping.json')


BILLMETA_GO_CMD = 'billmeta'
ESQUERY_GO_CMD = 'esquery'
COMPAREMATRIX_GO_CMD = 'comparematrix'
PATH_TO_CONGRESSDATA_DIR = CONGRESS_DATA_PATH
PATH_TO_DATA_DIR = os.getenv('PATH_TO_DATA_DIR', os.path.join('/', *"/usr/local/share/xcential/public/data".split('/')))
PATH_TO_CONGRESSDATA_XML_DIR = os.getenv('PATH_TO_CONGRESSDATA_XML_DIR', os.path.join('/', *"/usr/local/share/xcential/public/data/116/dtd".split('/')))
PATH_TO_RELATEDBILLS_DIR = os.path.join(PATH_TO_CONGRESSDATA_DIR, 'relatedbills')

USCONGRESS_XML_FILE = 'document.xml'

RESULTS_DEFAULT = 20
MIN_SCORE_DEFAULT = 25

try:
  BILLSECTION_MAPPING = json.loads(pkgutil.get_data(__name__, PATH_BILLSECTIONS_JSON).decode("utf-8"))
  BILL_FULL_MAPPING = json.loads(pkgutil.get_data(__name__, PATH_BILL_FULL_JSON).decode("utf-8"))
except Exception as err:

  with open(PATH_BILLSECTIONS_JSON, 'r') as f:
    BILLSECTION_MAPPING = json.load(f)

  with open(PATH_BILL_FULL_JSON, 'r') as f:
    BILL_FULL_MAPPING = json.load(f)


#PATH_TO_RELATEDBILLS = '../relatedBills.json'
SAVE_ON_COUNT = 1000

BILL_ID_REGEX = r'[a-z]+[1-9][0-9]*-[1-9][0-9]+'
BILL_NUMBER_PART_REGEX = r'(?P<congress>[1-9][0-9]*)(?P<stage>[a-z]+)(?P<number>[0-9]+)(?P<version>[a-z]+)?'
BILL_NUMBER_PART_REGEX_COMPILED = re.compile(BILL_NUMBER_PART_REGEX)
BILL_NUMBER_REGEX = BILL_NUMBER_PART_REGEX + '$'
BILL_DIR_REGEX = r'.*?([1-9][0-9]*)\/bills\/[a-z]+\/([a-z]+)([0-9]+)$'
BILL_NUMBER_REGEX_COMPILED = re.compile(BILL_NUMBER_REGEX)
BILL_DIR_REGEX_COMPILED = re.compile(BILL_DIR_REGEX)

# congress/data/117/bills/sconres/sconres2
US_CONGRESS_PATH_REGEX_COMPILED = re.compile(r'data\/(?P<congress>[1-9][0-9]*)\/(?P<doctype>[a-z]+)\/(?P<stage>[a-z]{1,8})\/(?P<billnumber>[a-z]{1,8}[1-9][0-9]*)\/?(text-versions\/)?(?P<version>[a-z]+)?')

BILL_TYPES = {
  'ih': 'introduced',
  'rh': 'reported to house'
}

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
    return 'data/{congress}/bills/{stage}{billnumber}/BILLS-{congress}{stage}{billnumber}{version}.xml'.format(**match.groupdict())
  else:
    return ''

def billNumberVersionFromPath_USCONGRESS(path: str):
  match = US_CONGRESS_PATH_REGEX_COMPILED.search(path)
  if match:
    return '{congress}{stage}{billnumber}{version}'.format(match.groupdict())
  else:
    return '' 

def billNumberVersionToPath_USCONGRESS(billnumber_version: str):
  match = BILL_NUMBER_PART_REGEX_COMPILED.search(billnumber_version)
  if match:
    return 'data/{congress}/bills/{stage}/{stage}{billnumber}/text-versions/{version}/document.xml'.format(**match.groupdict())
  else:
    return ''

CONGRESS_DIRS = {"congressdotgov": {
  "samplePath": "data/117/bills/hr200/BILLS-117hr200ih.xml",
  "billXMLFilenameRegex": r'BILLS-'+BILL_NUMBER_PART_REGEX+r'\.xml',
  "pathToBillnumberVersion": billNumberVersionFromPath_CDG,
  "billNumberVersionToPath": billNumberVersionToPath_CDG
  },
 "unitedstates": {
   "samplePath": f'congress/data/117/bills/sconres/sconres2/text-versions/ih/{USCONGRESS_XML_FILE}',
   "billXMLFilenameRegex": r''+USCONGRESS_XML_FILE,
   "pathToBillnumberVersion": billNumberVersionFromPath_USCONGRESS,
   "billNumberVersionToPath": billNumberVersionToPath_USCONGRESS
 },
 "lrc": {},
 }

CURRENT_CONGRESSIONAL_YEAR = datetime.date.today().year if datetime.date.today() > datetime.date(datetime.date.today().year, 1, 3) else (datetime.date.today().year - 1)
START_CONGRESS = 110 # Earliest Congress with data in our database
CURRENT_CONGRESS, cs_temp = divmod(round(((datetime.date(CURRENT_CONGRESSIONAL_YEAR, 1, 3) - datetime.date(1788, 1, 3)).days) / 365) + 1, 2)
CURRENT_SESSION = cs_temp + 1

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
      "must": [
         { "match": {
              "headers": {
              "query": "date"
              }
         }
        }
      ],
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
          "must": [
            { "match": { "sections.section_header": "title" }}
          ]
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
SAMPLE_QUERY_MLT_HEADERS  = {
  "size": RESULTS_DEFAULT,
  "min_score": MIN_SCORE_DEFAULT,
  "query": {
  "more_like_this": {
    "fields": ["headers"],
    "like": "Dependent care credit improvements",
    "min_term_freq" : 1,
    "max_query_terms" : 10,
    "min_doc_freq" : 1 
  }
}
}

reporting_requirement = """
Not later than 5 years after the date of enactment of this Act, the administering Secretaries, acting jointly, shall report to the appropriate committees of Congress on the progress in the reduction of food waste that can be attributed to the standardization of food date labeling and consumer education required by this Act and the amendments made by this Act
"""

quality_date_guidance = """
The Commissioner of Food and Drugs and the Secretary of Agriculture shall establish guidance for food labelers on how to determine quality dates and safety dates for food products.
"""

def getQueryText(text_path: str=''):
  with open(text_path, 'r') as f:
      queryText = f.read()
  if not queryText:
    queryText = ''
  return queryText

# more like this query (working)
SAMPLE_QUERY_NESTED_MLT = {
  "size": RESULTS_DEFAULT,
  "min_score": MIN_SCORE_DEFAULT,
  "query": {
    "nested": {
      "path": "sections",
      "query": {
        "more_like_this": {
          "fields": ["sections.section_text"],
          "like": reporting_requirement,
          "min_term_freq" : 2,
          "max_query_terms" : 30,
          "min_doc_freq" : 2 
        }
      },
      "inner_hits": {
          "highlight": {
          "fields": {
            "sections.section_text": {}
          }
        }
      }
    }
  }
}

def makeMLTQuery(queryText: str, queryTextPath: str=''):
  if queryTextPath and not queryText:
    try:
      queryText = getQueryText(queryTextPath)
    except Exception as err:
      raise Exception('Error getting text from path: {0}'.format(err))

  newQuery = deepcopy(SAMPLE_QUERY_NESTED_MLT)
  newQuery['query']['nested']['query']['more_like_this']['like'] = queryText 
  return newQuery
