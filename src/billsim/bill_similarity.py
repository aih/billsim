#!/usr/bin/env python3

import sys, os
import logging
from elasticsearch import exceptions, Elasticsearch

from billsim.pymodels import BillPath, BillSections, SimilarSection
from lxml import etree

es = Elasticsearch()
from billsim import constants
from billsim.utils import billNumberVersionToBillPath, deep_get, getId, getHeader, getEnum, getText
from billsim.pymodels import SectionMeta, Section

logging.basicConfig(filename='bill_similarity.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def getHitsHits(res) -> list:
    return res.get('hits').get('hits')


def getMinScore(queryText: str) -> int:
    """
    Returns the minimum score for a queryText, based on the length.
    If we scale the min_score by the length of the section, we may be able to use 'max' score_mode always.
    
    Minimum text length to get > 20 score in the 'max' score_mode is ~ 340 characters
    See, e.g.  `constants.misc_civil_rights` (section 9 of 117hr5ih)
    
    Args:
        queryText (str): The text of the query. 

    Returns:
        int: minimum score 
    """
    length = len(queryText)
    if length < 500:
        return 20
    elif length < 1000:
        return 40
    elif length < 1500:
        return 50
    else:
        return 60


def runQuery(index: str = constants.INDEX_SECTIONS,
             query: dict = constants.SAMPLE_QUERY_NESTED_MLT,
             size: int = constants.MAX_BILLS_SECTION) -> dict:
    """
  See API documentation
  https://elasticsearch-py.readthedocs.io/en/v7.10.1/api.html#elasticsearch.Elasticsearch.search
  """
    query = query
    return es.search(index=index, body=query, size=size)


def moreLikeThis(queryText: str,
                 index: str = constants.INDEX_SECTIONS,
                 score_mode: str = constants.SCORE_MODE_MAX,
                 size: int = constants.MAX_BILLS_SECTION,
                 min_score: int = constants.MIN_SCORE_DEFAULT) -> dict:
    if min_score == constants.MIN_SCORE_DEFAULT:
        min_score = getMinScore(queryText)
    query = constants.makeMLTQuery(queryText,
                                   min_score=min_score,
                                   score_mode=score_mode)
    return runQuery(index=index, query=query, size=size)


def getSimilarSections(
        queryText: str,
        min_score: int = constants.MIN_SCORE_DEFAULT) -> list[SimilarSection]:
    """
  Runs query for sections with 'max' score_mode;
  return in the form of a list of SimilarSection
  """

    res = moreLikeThis(queryText, min_score=min_score)
    hitsHits = getHitsHits(res)
    similarSections = []
    for hitsHit in hitsHits:
        similar_section_hits = deep_get(
            hitsHit, ["inner_hits", "sections", "hits", "hits"])
        if similar_section_hits and len(similar_section_hits) > 0:
            similar_section_hit = similar_section_hits[0]
            similar_section = SimilarSection(
                billnumber_version=deep_get(hitsHit, ["_source", "id"]),
                score_es=hitsHit.get("_score", 0),
                score=None,
                score_other=None,
                section_id=deep_get(similar_section_hit,
                                    ["_source", "section_id"]),
                label=deep_get(similar_section_hit,
                               ["_source", "section_number"]),
                header=deep_get(similar_section_hit,
                                ["_source", "section_header"]),
                length=deep_get(similar_section_hit,
                                ["_source", "section_length"]))
            similarSections.append(similar_section)
        else:
            pass
    return similarSections


# This function is independent of any bill number and is the basis for searching similarity for arbitrary text
def getSimilarSectionItem(
        queryText: str,
        sectionMeta: SectionMeta,
        min_score: int = constants.MIN_SCORE_DEFAULT) -> Section:
    similar_sections = getSimilarSections(queryText, min_score=min_score)
    return Section(similar_sections=similar_sections,
                   billnumber_version=sectionMeta.billnumber_version,
                   section_id=sectionMeta.section_id,
                   label=sectionMeta.label,
                   header=sectionMeta.header,
                   length=sectionMeta.length)


def getSimilarDocSections(filePath: str, docId: str) -> list[Section]:
    try:
        billTree = etree.parse(filePath, etree.XMLParser())

    except:
        raise Exception('Could not parse bill')
    sections = billTree.xpath('//section[not(ancestor::section)]')

    sectionsList = []
    for section in sections:
        section_text = etree.tostring(section,
                                      method="text",
                                      encoding="unicode")
        length = len(section_text)
        header = getHeader(section)
        enum = getEnum(section)
        if (len(header) > 0 and len(enum) > 0):
            section_meta = SectionMeta(billnumber_version=docId,
                                       label=enum,
                                       header=header,
                                       section_id=getId(section),
                                       length=length)
        else:
            section_meta = SectionMeta(billnumber_version=docId,
                                       section_id=getId(section),
                                       label=None,
                                       header=None,
                                       length=length)
        sectionsList.append(
            getSimilarSectionItem(queryText=section_text,
                                  sectionMeta=section_meta))
    return sectionsList


def getSimilarBillSections(billnumber_version: str = None,
                           bill_path: BillPath = None,
                           pathType: str = "congressdotgov") -> BillSections:
    """
  Get similar sections for a bill.
  This function is a wrapper for getSimilarSectionItem and assumes a billnumber_version or BillPath 
  For a generic document, run getSimilarDocSections 

  Args:
      billnumber_version (str): bill number and version.
      bill_path (BillPath): BillPath object, with billnumber_version and path 
  NOTE: Only one of billnumber_version and bill_path should be specified.

  Raises:
      Exception: exception upon incorrect args or upon parsing bill or opening the bill xml file 

  Returns:
      BillSections: a BillSections object, with similar sections for the bill 
  """
    if bill_path is not None and billnumber_version is not None:
        raise Exception(
            "bill_path and billnumber_version cannot be specified together")

    if bill_path is None:
        if billnumber_version is not None:
            bill_path = billNumberVersionToBillPath(
                billnumber_version=billnumber_version, pathType=pathType)
        else:
            raise Exception("bill_path or billnumber_version must be specified")

    if not os.path.isfile(bill_path.filePath):
        logger.error("Bill file does not exist: %s", bill_path.filePath)
        raise Exception("Bill file does not exist: %s", bill_path.filePath)

    sectionsList = getSimilarDocSections(filePath=bill_path.filePath,
                                         docId=bill_path.billnumber_version)
    doc_length = 0
    with open(bill_path.filePath, 'r') as f:
        billText = f.read()
        doc_length = len(billText)

    return BillSections(billnumber_version=bill_path.billnumber_version,
                        length=doc_length,
                        sections=sectionsList)
