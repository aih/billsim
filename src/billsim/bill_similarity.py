#!/usr/bin/env python3

from elasticsearch import exceptions, Elasticsearch
es = Elasticsearch()
from billsim import constants

def runQuery(index: str=constants.INDEX_SECTIONS, query: dict=constants.SAMPLE_QUERY_NESTED_MLT, size: int=constants.MAX_BILLS_SECTION) -> dict:
  query = query
  # See API documentation
  # https://elasticsearch-py.readthedocs.io/en/v7.10.1/api.html#elasticsearch.Elasticsearch.search
  return es.search(index=index, body=query, size=size)

def moreLikeThis(queryText: str, index: str=constants.INDEX_SECTIONS, score_mode: str=constants.SCORE_MODE_MAX, size: int=constants.MAX_BILLS_SECTION) -> dict:
  query = constants.makeMLTQuery(queryText, score_mode=score_mode)
  return runQuery(index=index, query=query, size=size)