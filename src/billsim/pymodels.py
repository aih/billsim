#!/usr/bin/env python3

from pydantic import BaseModel

class Status(BaseModel):
    success: bool
    message: str 


class BillPath(BaseModel):
    billnumber_version: str = ''
    path: str = ''
    fileName: str = '' 

class SimilarSection(BaseModel):
    from_section_id: str
    to_section_id: str
    from_section_label: str
    to_section_label: str
    from_section_header: str
    to_section_header: str
    score_es: float
    score: float
    score_other: float


class SimilarBill(BaseModel):
    id: int
    billnumber_version: str
    score: float
    score_other: float
    reason: str
    billnumber_to: str
    identified_by: str
    title: str
    similar_sections: list[SimilarSection]


