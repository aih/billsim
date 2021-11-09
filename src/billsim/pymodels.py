#!/usr/bin/env python3

from pydantic import BaseModel


class Status(BaseModel):
    success: bool
    message: str


class BillPath(BaseModel):
    billnumber_version: str = ''
    path: str = ''
    fileName: str = ''

class SectionMeta(BaseModel):
    billnumber_version: str
    id: str
    label: str
    header: str
    length: int

class SimilarSection(SectionMeta):
    score_es: float
    score: float
    score_other: float


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
    length: int
    score: float
    score_other: float
    reasons: list[str] 
    billnumber_version_to: str
    identified_by: str
    title: str
    title_to: str
    sections: list[
        Section]  # for BillToBill, the Section.sections has just the highest scoring similar section between the bills
