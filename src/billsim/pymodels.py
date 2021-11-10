#!/usr/bin/env python3

from pydantic import BaseModel
from typing import Optional


class Status(BaseModel):
    success: bool
    message: str


class BillPath(BaseModel):
    billnumber_version: str = ''
    path: str = ''
    fileName: str = ''

class SectionMeta(BaseModel):
    billnumber_version: Optional[str] = None
    section_id: Optional[str] = None
    label: Optional[str] = None
    header: Optional[str] = None
    length: Optional[int] = None

class SimilarSection(SectionMeta):
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_other: Optional[float] = None


class Section(SectionMeta):
    similar_sections: list[SimilarSection]


# Result of the similarity search, collecting top similar sections for each section of the bill
class BillSections(BaseModel):
    id: int
    billnumber_version: str
    length: int
    title: str
    sections: list[Section]


class BillToBill(BaseModel):
    id: int
    billnumber_version: str
    length: Optional[int] = None
    length_to: Optional[int] = None
    score_es: Optional[float] = None
    score: float
    score_other: float
    reasons: list[str] 
    billnumber_version_to: str
    identified_by: str
    title: str
    title_to: str
    sections: list[
        Section]  # for BillToBill, the Section.sections has just the highest scoring similar section between the bills


# The hits.hits array of the similarity search is made up of items of the form:
"""
 {
        "_index" : "billsim",
        "_type" : "_doc",
        "_id" : "-Zw7_nwBUuoHSnHyN3tm",
        "_score" : 97.14994,
        "_source" : {
          "congress" : "116",
          "session" : "1",
          "id" : "116hr5rh"
        },
        "inner_hits" : {
          "sections" : {
            "hits" : {
              "total" : {
                "value" : 16,
                "relation" : "eq"
              },
              "max_score" : 97.14994,
              "hits" : [
                {
                  "_index" : "billsim",
                  "_type" : "_doc",
                  "_id" : "-Zw7_nwBUuoHSnHyN3tm",
                  "_nested" : {
                    "field" : "sections",
                    "offset" : 2
                  },
                  "_score" : 97.14994,
                  "_source" : {
                    "section_number" : "3.",
                    "section_header" : "Public accommodations"
                  }
                },
                {
                  "_index" : "billsim",
                  "_type" : "_doc",
                  "_id" : "-Zw7_nwBUuoHSnHyN3tm",
                  "_nested" : {
                    "field" : "sections",
                    "offset" : 7
                  },
                  "_score" : 41.923565,
                  "_source" : {
                    "section_number" : "7.",
                    "section_header" : "Employment"
                  }
                },
                {
                  "_index" : "billsim",
                  "_type" : "_doc",
                  "_id" : "-Zw7_nwBUuoHSnHyN3tm",
                  "_nested" : {
                    "field" : "sections",
                    "offset" : 1
                  },
                  "_score" : 41.48145,
                  "_source" : {
                    "section_number" : "2.",
                    "section_header" : "Findings and purpose"
                  }
                }
              ]
            }
          }
        }
      }
"""
class SimilarSectionHit(BaseModel):
    billnumber_version: str # from _source.id
    score: float # from _score


































































