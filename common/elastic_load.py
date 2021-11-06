
import re
import json
from lxml import etree
from elasticsearch import exceptions, Elasticsearch
es = Elasticsearch()
from common.utils import getText
from common import constants
from common.pymodels import Status, BillPath, SimilarBill, SimilarSection

def getMapping(map_path: str) -> dict:
    with open(map_path, 'r') as f:
        return json.load(f)

# For future possible improvements, see https://www.is.inf.uni-due.de/bib/pdf/ir/Abolhassani_Fuhr_04.pdf
# Applying the Divergence From Randomness Approach for Content-Only Search in XML Documents
def createIndex(index: str='billsections', body: dict=constants.BILLSECTION_MAPPING, delete=False):
  if delete:
    try:
      es.indices.delete(index=index)
    except exceptions.NotFoundError:
      print('No index to delete: {0}'.format(index))

  print('Creating index with mapping: ')
  print(str(body))
  es.indices.create(index=index, ignore=400, body=body)

def getEnum(section) -> str:
  enumpath = section.xpath('enum')  
  if len(enumpath) > 0:
    return enumpath[0].text
  return ''

def getHeader(section) -> str:
  headerpath = section.xpath('header')  
  if len(headerpath) > 0:
    return headerpath[0].text
  return ''

def indexBill(bill_path: str, billnumber_version: str, index_types: list=['sections']) -> Status:
  """
  Index bill with Elasticsearch

  Args:
      bill_path (str): location of the bill xml file.
      billnumber_version (str): bill number and version, of the form 117hr200ih.
      index_types (list, optional): Index by 'sections', 'bill_full' or both. Defaults to ['sections'].

  Raises:
      Exception: [description]

  Returns:
      Status: status of the indexing of the form {success: True/False, message: 'message'}} 
  """
  try:
    billTree = etree.parse(bill_path, parser=etree.XMLParser())
  except:
    raise Exception('Could not parse bill')
  dublinCores = billTree.xpath('//dublinCore')
  if (dublinCores is not None) and (len(dublinCores) > 0):
    dublinCore = etree.tostring(dublinCores[0], method="xml", encoding="unicode"),
  else:
    dublinCore = ''
  dcdate = getText(billTree.xpath('//dublinCore/dc:date', namespaces={'dc': 'http://purl.org/dc/elements/1.1/'}))
  # TODO find date for enr bills in the bill status (for the flat congress directory structure)
  if (dcdate is None or len(dcdate) == 0) and  '/data.xml' in bill_path:
    metadata_path = bill_path.replace('/data.xml', '/data.json')
    try:
      with open(metadata_path, 'rb') as f:
        metadata = json.load(f)
        dcdate = metadata.get('issued_on', None)
    except:
      pass
  if dcdate is None or len(dcdate) == 0:
    dcdate = None 

  congress = billTree.xpath('//form/congress')
  congress_text = re.sub(r'[a-zA-Z ]+$', '', getText(congress))
  session = billTree.xpath('//form/session')
  session_text = re.sub(r'[a-zA-Z ]+$', '', getText(session))
  legisnum = billTree.xpath('//legis-num')
  legisnum_text = getText(legisnum)
  dctitle = getText(billTree.xpath('//dublinCore/dc:title', namespaces={'dc': 'http://purl.org/dc/elements/1.1/'}))

  doc_id = ''
  billMatch = constants.BILL_NUMBER_REGEX_COMPILED.match(billnumber_version)
  billversion = ''
  billnumber = ''
  if billMatch:
    billMatchGroup = billMatch.groupdict()
    billnumber = billMatchGroup.get('congress', '') + billMatchGroup.get('stage', '') + billMatchGroup.get('number', '')
    billversion = billMatchGroup.get('version', '') 
  sections = billTree.xpath('//section')
  headers = billTree.xpath('//header')
  from collections import OrderedDict
  headers_text = [ header.text for header in headers]

  # Uses an OrderedDict to deduplicate headers
  # TODO handle missing header and enum separately
  if 'sections' in index_types:
    doc = {
        'id': billnumber_version,
        'congress': congress_text,
        'session': session_text,
        'dc': dublinCore,
        'dctitle': dctitle,
        'date': dcdate,
        'legisnum': legisnum_text,
        'billnumber': billnumber,
        'billversion': billversion,
        'headers': list(OrderedDict.fromkeys(headers_text)),
        'sections': [{
            'section_number': getEnum(section) ,
            'section_header':  getHeader(section),
            'section_text': etree.tostring(section, method="text", encoding="unicode"),
            'section_xml': etree.tostring(section, method="xml", encoding="unicode")
        } if (section.xpath('header') and len(section.xpath('header')) > 0  and section.xpath('enum') and len(section.xpath('enum'))>0) else
        {
            'section_number': '',
            'section_header': '', 
            'section_text': etree.tostring(section, method="text", encoding="unicode"),
            'section_xml': etree.tostring(section, method="xml", encoding="unicode")
        } 
        for section in sections ]
    } 
  
    # If the document has no identifiable bill number, it will be indexed with a random id
    # This will make retrieval and updates ambiguous
    if doc_id != '' and len(doc_id) > 7:
        doc['id'] = doc_id

    res = es.index(index="billsections", body=doc)

  if 'bill_full' in index_types:
    billText = etree.tostring(billTree, method="text", encoding="unicode") 
    doc_full = {
      'id': billnumber_version,
      'congress': congress_text,
      'session': session_text,
      'dc': dublinCore,
      'dctitle': dctitle,
      'date': dcdate,
      'legisnum': legisnum_text,
      'billnumber': billnumber,
      'billversion': billversion,
      'headers': list(OrderedDict.fromkeys(headers_text)),
      'billtext': billText
    }
    res = es.index(index="bill_full", body=doc_full)
  # TODO: check res for status before returning Status
  return Status(success=True, message='Indexed bill')

    # billRoot = billTree.getroot()
    # nsmap = {k if k is not None else '':v for k,v in billRoot.nsmap.items()}