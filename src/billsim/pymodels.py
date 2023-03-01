#!/usr/bin/env python3

from sqlalchemy.sql.schema import UniqueConstraint, Index
from sqlalchemy.sql.sqltypes import ARRAY, VARCHAR, String
from sqlalchemy.ext.declarative import declared_attr
from sqlmodel import Field, SQLModel, Column, Integer, Sequence
from typing import List, Optional
from billsim.database import engine
from datetime import datetime


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
    __table_args__ = (UniqueConstraint('billnumber',
                                       'version',
                                       name='billnumber_version'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    length: Optional[int] = None
    # TODO: when indexing/storing Bill initially, calculate number of sections
    #sections_num: Optional[int] = None
    billnumber: str = Field(index=True)
    version: str = Field(index=True)

    @classmethod
    def getBillnumberversion(cls):
        return "{cls.billnumber}{cls.version}".format(cls=cls)

class UploadedDoc(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('billnumber',
                                       'version',
                                       name='uploaded_billnumber_version'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    # The doc_id is an externally provided id for the document
    ext_id: Optional[int] = Field(index=True, default=None)
    length: Optional[int] = None
    # TODO: when indexing/storing Bill initially, calculate number of sections
    #sections_num: Optional[int] = None
    billnumber: str = Field(index=True)
    version: str = Field(index=True)
    user: Optional[str] = None
    processed: bool = Field(default=False)

    @classmethod
    def getBillnumberversion(cls):
        return "{cls.billnumber}{cls.version}".format(cls=cls)


class CurrencyModel(SQLModel, table=True):
    currency_id: Optional[int] = Field(default=None, primary_key=True)
    version: Optional[str] = Field(default=None)
    date: Optional[datetime] = None

class BillToBillModel(SQLModel):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id",
                                      primary_key=True)
    billnumber_version: str = Field(index=True)
    billnumber_version_to: str = Field(index=True)
    billnumber: Optional[str] = Field(index=True)
    version: Optional[str] = Field(index=True)
    billnumber_to: Optional[str] = Field(index=True)
    version_to: Optional[str] = Field(index=True)
    titles: Optional[dict] = None
    titles_to: Optional[dict] = None
    title: Optional[str] = None
    title_to: Optional[str] = None
    length: Optional[int] = None
    length_to: Optional[int] = None
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasons: Optional[List[str]] = Field(default=None,
                                         sa_column=Column(ARRAY(String)))
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    sections: Optional[list[
        Section]] = None    # for BillToBill, the Section.sections has just the highest scoring similar section between the bills
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")



class BillModelDeep(SQLModel):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    billnumber_version: Optional[str] = Field(index=True)
    billnumber: Optional[str] = Field(index=True)
    version: Optional[str] = Field(index=True)
    titles: Optional[dict] = None
    title: Optional[str] = None
    length: Optional[int] = None
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasons: Optional[List[str]] = Field(default=None,
                                         sa_column=Column(ARRAY(String)))
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    sections: Optional[list[Section]] = None    #


class BillToBillModelDeep(SQLModel):
    bill: BillModelDeep
    bill_to: BillModelDeep
    reasons: Optional[List[str]] = Field(default=None,
                                         sa_column=Column(ARRAY(String)))
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    sections: Optional[list[
        Section]] = None    # for BillToBill, the Section.sections has just the highest scoring similar section between the bills


# Model used to store in db
class BillToBill(SQLModel, table=True):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id",
                                      primary_key=True)
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasonsstring: Optional[str] = Field(default=None,
                                         sa_column=Column(VARCHAR(100)))
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")

# Model used to store in db
class UBillToBill(SQLModel, table=True):
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="uploadeddoc.id",
                                   primary_key=True)
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id",
                                      primary_key=True)
    score_es: Optional[float] = None
    score: Optional[float] = None
    score_to: Optional[float] = None
    reasonsstring: Optional[str] = Field(default=None,
                                         sa_column=Column(VARCHAR(100)))
    identified_by: Optional[str] = None
    sections_num: Optional[int] = None
    sections_match: Optional[int] = None
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")


# NOTES:
# 1. section_id_attr is the id attribute from the XML. It may not be unique.
#    However, the SQL bill_id + section_id is unique.
# 2. bill_id is both a foreign key, and part of a composite primary key.
class SectionItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('billnumber_version',
                                       'section_id_attr',
                                       name='billnumber_version_section_id'),)
    id: int = Field(sa_column=Column('id',Integer,Sequence("section_id_seq", start=1),primary_key=True))
    bill_id: Optional[int] = Field(default=None, foreign_key="bill.id")
    billnumber_version: Optional[str] = Field(default=None)
    section_id_attr: Optional[str] = Field(default=None)
    identifier: Optional[str] = Field(default=None, index=True)
    number: Optional[str] = Field(default=None, index=True)
    header: Optional[str] = Field(default=None, index=True)
    length: int

class USectionItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('billnumber_version',
                                       'section_id_attr',
                                       name='uploaded_billnumber_version_section_id'),)
    id: int = Field(sa_column=Column('id',Integer,Sequence("usection_id_seq", start=1),primary_key=True))
    bill_id: Optional[int] = Field(default=None, foreign_key="uploadeddoc.id")
    billnumber_version: Optional[str] = Field(default=None)
    section_id_attr: Optional[str] = Field(default=None)
    identifier: Optional[str] = Field(default=None, index=True)
    number: Optional[str] = Field(default=None, index=True)
    header: Optional[str] = Field(default=None, index=True)
    length: int


class SectionToSectionModel(SQLModel):
    """
    This table is used in-memory, before the indexes for bills and sections are known
    """    
    bill_number: Optional[str] = Field(default=None,
                                   primary_key=True)
    bill_number_to: Optional[str] = Field(default=None,
                                      primary_key=True)
    section_id: Optional[str] = Field(default=None)
    section_to_id: Optional[str] = Field(default=None)
    from_idx: Optional[int] = Field(default=None)
    to_idx: Optional[int] = Field(default=None)
    score: Optional[float] = None
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")


class SectionToSection(SQLModel, table=True):
    """
    This table is indexed by the matched bills. It is a one-to many relation, 
    so for each pair of bill_id, bill_to_id, we get a list of matched sections.
    """
    __table_args__ = (Index('sectionmatch_index', 'bill_id','bill_to_id'),)
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id")
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id")
    section_id: Optional[int] = Field(default=None, primary_key=True,
                              foreign_key="sectionitem.id")
    section_to_id: Optional[int] = Field(default=None, primary_key=True,
                                 foreign_key="sectionitem.id")
    score: Optional[float] = None
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")

class USectionToSection(SQLModel, table=True):
    """
    This table is indexed by the matched bills. It is a one-to many relation, 
    so for each pair of bill_id, bill_to_id, we get a list of matched sections.
    """
    __table_args__ = (Index('uploaded_sectionmatch_index', 'bill_id','bill_to_id'),)
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="uploadeddoc.id")
    bill_to_id: Optional[int] = Field(default=None,
                                      foreign_key="bill.id")
    section_id: Optional[int] = Field(default=None, primary_key=True,
                              foreign_key="usectionitem.id")
    section_to_id: Optional[int] = Field(default=None, primary_key=True,
                                 foreign_key="sectionitem.id")
    score: Optional[float] = None
    currency_id: Optional[int] = Field(default=None, foreign_key="currencymodel.currency_id")


# From billtitles-py
class Title(SQLModel, table=True):
    __tablename__ = "titles"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)


class BillTitle(SQLModel, table=True):
    __tablename__ = "bill_titles"

    title_id: Optional[int] = Field(default=None,
                                    foreign_key="titles.id",
                                    primary_key=True)
    bill_id: Optional[int] = Field(default=None,
                                   foreign_key="bill.id",
                                   primary_key=True)
    is_for_whole_bill: bool = Field(default=False)


# For display (from billtitles-py)
class BillTitlePlus(SQLModel):

    id: Optional[int] = Field(default=None, primary_key=True)
    billnumber: str = Field(index=True)
    titles: str
    is_for_whole_bill: bool = Field(default=False)


class TitlesItem(SQLModel):
    whole: List[str]
    all: List[str]


class BillTitleResponse(SQLModel):
    billnumber: str
    titles: TitlesItem


class TitleBillsResponseItem(SQLModel):
    id: int
    title: str
    billnumbers: List[str]


class TitleBillsResponse(SQLModel):
    titles: List[TitleBillsResponseItem]
    titles_whole: List[TitleBillsResponseItem]


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_db_and_tables()