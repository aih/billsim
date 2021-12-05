#!/usr/bin/env python3

from sqlalchemy.sql.schema import UniqueConstraint
from sqlmodel import Field, SQLModel, Session, create_engine
from typing import Optional
from billsim.database import engine


class Status(SQLModel):
    success: bool
    message: str


class BillPath(SQLModel):
    billnumber_version: str = ''
    filePath: str = ''
    fileName: str = ''


class SectionMeta(SQLModel):
    billnumber_version: Optional[str] = None
    section_id: Optional[str] = None
    label: Optional[str] = None
    header: Optional[str] = None
    length: Optional[int] = None


class SimilarSection(SectionMeta):
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None


class Section(SectionMeta):
    similar_sections: list[SimilarSection]


# This is the basis for making queries, using billsim.bill_similarity.py getSimilarSectionItem
class QuerySection(SectionMeta):
    query_text: str


# Result of the similarity search, collecting top similar sections for each section of the bill
class BillSections(SQLModel):
    billnumber_version: str
    length: int
    sections: list[Section]


class SimilarSectionHit(SQLModel):
    billnumber_version: str    # from _source.id
    score: float    # from _score


class Bill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    length: Optional[int] = None
    # TODO: when indexing/storing Bill initially, calculate number of sections
    #sections_num: Optional[int] = None
    billnumber: str
    version: str

    @classmethod
    def getBillnumberversion(cls):
        return "{cls.billnumber}{cls.version}".format(cls=cls)

    UniqueConstraint('billnumber', 'version', name='billnumber_version')


class BillToBillModel(SQLModel):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id",
                                      primary_key=True)
    billnumber_version: str
    length: Optional[int] = None
    billnumber_version_to: str
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasons: Optional[list[str]] = []
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    sections: list[
        Section]    # for BillToBill, the Section.sections has just the highest scoring similar section between the bills


# Model used to store in SQLite
class BillToBillLite(SQLModel, table=True):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id",
                                      primary_key=True)
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasons: Optional[list[str]] = None
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_matched: Optional[int] = None
    #sections: Optional[
    #    str] = None


# NOTE: section_id is the id attribute from the XML. It may not be unique.
# However, the SQL bill_id + section_id is unique.
class SectionItem(SQLModel, table=True):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    section_id: Optional[str] = Field(default=None, primary_key=True)
    label: str
    header: str
    length: int


class SectionToSection(SQLModel, table=True):
    """
    This is a self-join of the SectionItem table.
    """
    section_id: Optional[str] = Field(default=None,
                                      foreign_key="sectionitem.id",
                                      primary_key=True)
    section_id_to: Optional[str] = Field(default=None,
                                         foreign_key="sectionitem.id",
                                         primary_key=True)
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_db_and_tables()