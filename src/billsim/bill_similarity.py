#!/usr/bin/env python3

from elasticsearch import exceptions, Elasticsearch
es = Elasticsearch()
from billsim import constants

def runQuery(index: str=constants.INDEX_SECTIONS, query: dict=constants.SAMPLE_QUERY_NESTED_MLT, size: int=50) -> dict:
  query = query
  # See API documentation
  # https://elasticsearch-py.readthedocs.io/en/v7.10.1/api.html#elasticsearch.Elasticsearch.search
  return es.search(index=index, body=query, size=size)

def moreLikeThis(queryText: str, index: str=constants.INDEX_SECTIONS):
  query = constants.makeMLTQuery(queryText)
  return runQuery(index=index, query=query, size=constants.MAX_BILLS_SECTION)