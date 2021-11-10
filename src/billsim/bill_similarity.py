#!/usr/bin/env python3

from elasticsearch import exceptions, Elasticsearch

es = Elasticsearch()
from billsim import constants
from pymodels import SectionMeta, Section

def getHitsHits(res):
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
    query = query
    # See API documentation
    # https://elasticsearch-py.readthedocs.io/en/v7.10.1/api.html#elasticsearch.Elasticsearch.search
    return es.search(index=index, body=query, size=size)


def moreLikeThis(queryText: str,
                 index: str = constants.INDEX_SECTIONS,
                 score_mode: str = constants.SCORE_MODE_MAX,
                 size: int = constants.MAX_BILLS_SECTION) -> dict:
    min_score = getMinScore(queryText)
    query = constants.makeMLTQuery(queryText,
                                   min_score=min_score,
                                   score_mode=score_mode)
    return runQuery(index=index, query=query, size=size)

    # TODO run query section with 'max' score_mode;
    # return in the form of a Section

def getSimilarSections(queryText: str) -> Section:

    res = moreLikeThis(queryText)
    hitsHits = getHitsHits(res)
    for hitsHit in hitsHits:
        # TODO: 
        # billnumber_version = hitsHit._source.id
        # billnumber_version = _source.id
        # score_es = hitsHit._score
        # section_id = hitsHit._source.section_id
        # label = hitsHit._source.section_number
        # header = hitsHit._source.section_header
        # length = hitsHit._source.section_length
    
        
