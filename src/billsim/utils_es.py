#!/usr/bin/env python3
from copy import deepcopy
import sys
import logging
from elasticsearch import exceptions, Elasticsearch
from billsim import constants
from billsim.pymodels import SectionMeta, QuerySection

es = Elasticsearch()

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


def getBill_es(billnumber: str,
               version: str = '',
               index: str = constants.INDEX_SECTIONS):
    """
    Get a bill or bills from Elasticsearch by billnumber or billnumber + version.
    If billnumber + version 

    Args:
        billnumber (str): billnumber of the form '116hr2500' 
        version (str, optional): version of the form 'ih', 'eh', 'enr', etc. Defaults to ''.
        index (str, optional): [description]. Defaults to constants.INDEX_SECTIONS.

    Returns:
        list of _source document: a list of the [_source] field of the es document, of the form:
         "id" : "116hr200ih",
          "congress" : "116",
          "session" : "1",
          "dctitle" : "116 HR 200 IH: Border Wall Trust Fund Act",
          "date" : "2019-01-03",
          "legisnum" : "H. R. 200",
          "billnumber" : "116hr200",
          "billversion" : "ih",
          "headers" : [
              ...
          "sections" : [
              {
              "section_id" : "H5C8DB8032CB347B989A81DF3CAA1167F",
              "section_number" : "1.",
              "section_header" : "Short title",
              "section_text" : "1.Short titleThis Act may be cited as the Border Wall Trust Fund Act. ",
              "section_length" : 70,
              "section_xml" : "<secti...},
              ...
    """
    try:
        if version != '':
            logger.debug(f'Getting bill {billnumber} version {version}')
            billnumber_version = billnumber + version
            res = es.get(index=index, id=billnumber_version)
        else:
            logger.warning(f'Getting bill {billnumber} without version')
            query = deepcopy(constants.SAMPLE_MATCH_BILLNUMBER_QUERY)
            query['query']['match']['billnumber'] = billnumber
            res = runQuery(index=index, query=query)

        if res.get('_source'):
            return [res['_source']]
        else:
            return [item['_source'] for item in getHitsHits(res)]
    except exceptions.NotFoundError:
        logger.error(f'No bill found in Elasticsearch index for {billnumber}')
        return None


def esSourceToQueryData(source: dict) -> list[QuerySection]:
    """
    Convert the _source field of an Elasticsearch document to a list of bill sections.
    Args:
        source (dict): _source field of an Elasticsearch document.

    Returns:
        list[QuerySection]: a list of items with SectionMeta and query_text.
    """

    # In general, the billnumber_version is also the `id` of the es source.
    billnumber_version = source['billnumber'] + source['billversion']
    sections = source.get('sections')
    if sections is None or len(sections) == 0:
        return []
    return [
        QuerySection(billnumber_version=billnumber_version,
                     section_id=section.get('section_id', ''),
                     label=section.get('section_number', ''),
                     header=section.get('section_header', ''),
                     length=section.get('section_length', 0),
                     query_text=section.get('section_text'))
        for section in sections
    ]
