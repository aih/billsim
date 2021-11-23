#!/usr/bin/env python3

import sys, os
import logging
from elasticsearch import Elasticsearch

from billsim.pymodels import BillPath, BillSections, SimilarSection, BillToBillModel
from billsim.elastic_load import getDefaultNamespace
from lxml import etree

es = Elasticsearch()
from billsim import constants
from billsim.utils import billNumberVersionToBillPath, deep_get, getBillLengthbyPath, getId, getHeader, getEnum
from billsim.pymodels import SectionMeta, Section
from billsim.utils_es import getHitsHits, moreLikeThis

logging.basicConfig(filename='bill_similarity.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def getSimilarSections(
        queryText: str,
        index: str = constants.INDEX_SECTIONS,
        min_score: int = constants.MIN_SCORE_DEFAULT) -> list[SimilarSection]:
    """
  Runs query for sections with 'max' score_mode;
  return in the form of a list of SimilarSection
  """

    res = moreLikeThis(queryText, index, min_score=min_score)
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
                score_to=None,
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
        index: str = constants.INDEX_SECTIONS,
        min_score: int = constants.MIN_SCORE_DEFAULT) -> Section:
    similar_sections = getSimilarSections(queryText,
                                          index=index,
                                          min_score=min_score)
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
        logger.error("Error parsing file: {}; {} ", filePath, e)
        raise Exception('Could not parse bill: {}', filePath)
    defaultNS = getDefaultNamespace(billTree)
    if defaultNS is None:
        sections = billTree.xpath('//section[not(ancestor::section)]')
    else:
        sections = billTree.xpath('//ns:section[not(ancestor::ns:section)]',
                                  namespaces={'ns': defaultNS})

    sectionsList = []
    for section in sections:
        section_text = etree.tostring(section,
                                      method="text",
                                      encoding="unicode")
        length = len(section_text)
        header = getHeader(section, defaultNS)
        enum = getEnum(section, defaultNS)
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


def getSimilarBillSections(
        billnumber_version: str = None,
        bill_path: BillPath = None,
        pathType: str = constants.PATHTYPE_DEFAULT) -> BillSections:
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

    doc_length = getBillLengthbyPath(bill_path.filePath)
    sectionsList = getSimilarDocSections(filePath=bill_path.filePath,
                                         docId=bill_path.billnumber_version)

    return BillSections(billnumber_version=bill_path.billnumber_version,
                        length=doc_length,
                        sections=sectionsList)


def getBillToBill(billsections: BillSections) -> dict:
    billToBills = {}
    if len(billsections.sections) == 0:
        return billToBills
    # billsections.sections is a list[Section]
    for section in billsections.sections:
        # similar_sections is a list[SimilarSection]
        similar_sections = section.similar_sections
        if similar_sections is None or len(similar_sections) == 0:
            continue
        for similar_section in similar_sections:
            billnumber_version = similar_section.billnumber_version
            if billnumber_version is None:
                billnumber_version = ''
            if (billToBills.get(similar_section.billnumber_version) is None):
                billToBills[
                    similar_section.billnumber_version] = BillToBillModel(
                        billnumber_version=billsections.billnumber_version,
                        length=billsections.length,
                        score_es=similar_section.score_es,
                        billnumber_version_to=billnumber_version,
                        sections_num=len(billsections.sections),
                        sections=[
                            Section(billnumber_version=billsections.
                                    billnumber_version,
                                    section_id=section.section_id,
                                    label=section.label,
                                    header=section.header,
                                    similar_sections=[similar_section])
                        ])
            else:
                billToBills[similar_section.billnumber_version].sections.append(
                    Section(billnumber_version=billsections.billnumber_version,
                            section_id=section.section_id,
                            label=section.label,
                            header=section.header,
                            similar_sections=[similar_section]))
                billToBills[
                    similar_section.
                    billnumber_version].score_es += similar_section.score_es
    for billToBillKey in billToBills:
        billToBills[billToBillKey].sections_match = len(
            billToBills[billToBillKey].sections)
    return billToBills