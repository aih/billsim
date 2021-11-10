#!/usr/bin/env python3

from elasticsearch import exceptions, Elasticsearch

from billsim.pymodels import SimilarSection

es = Elasticsearch()
from billsim import constants
from billsim.utils import deep_get
from billsim.pymodels import SectionMeta, Section


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


# Runs query for sections with 'max' score_mode;
# return in the form of a list of SimilarSection
def getSimilarSections(queryText: str) -> list[SimilarSection]:

  res = moreLikeThis(queryText)
  hitsHits = getHitsHits(res)
  similarSections = []
  for hitsHit in hitsHits:
    similar_section_hits = deep_get(hitsHit,
                                    ["inner_hits", "sections", "hits", "hits"])
    if similar_section_hits and len(similar_section_hits) > 0:
      similar_section_hit = similar_section_hits[0]
      similar_section = SimilarSection(
          billnumber_version=deep_get(hitsHit, ["_source", "id"]),
          score_es=hitsHit.get("_score", 0),
          score=None,
          score_other=None,
          section_id=deep_get(similar_section_hit, ["_source", "section_id"]),
          label=deep_get(similar_section_hit, ["_source", "section_number"]),
          header=deep_get(similar_section_hit, ["_source", "section_header"]),
          length=deep_get(similar_section_hit, ["_source", "section_length"]))
      similarSections.append(similar_section)
    else:
      pass
  return similarSections


def getSimilarSectionItem(queryText: str, sectionMeta: SectionMeta) -> Section:
  similar_sections = getSimilarSections(queryText)
  return Section(similar_sections=similar_sections,
                 billnumber_version=sectionMeta.billnumber_version,
                 section_id=sectionMeta.section_id,
                 label=sectionMeta.label,
                 header=sectionMeta.header,
                 length=sectionMeta.length)
