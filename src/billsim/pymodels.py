#!/usr/bin/env python3

from pydantic import BaseModel
from typing import Optional


class Status(BaseModel):
    success: bool
    message: str


class BillPath(BaseModel):
    billnumber_version: str = ''
    filePath: str = ''
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
    billnumber_version: str
    length: int
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
        Section]    # for BillToBill, the Section.sections has just the highest scoring similar section between the bills


class SimilarSectionHit(BaseModel):
    billnumber_version: str    # from _source.id
    score: float    # from _score
