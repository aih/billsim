#!/usr/bin/env python3

import sys
import logging
from typing import Optional
from lxml import etree
from sqlalchemy.orm import Session
from billsim.utils import getDefaultNamespace, getBillLength, getBillLengthbyPath, getBillnumberversionParts, getId, getEnum, getText
from billsim.database import SessionLocal
from billsim import pymodels, constants

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(level='INFO')
""" 
Take the Section object (which consists of the from Section Meta and a list of similar sections)
 returned in bill_similarity.getBillToBill()
 Save a) the from section and each similar section, in the SectionItem table if it does not exist,
 and b) the similarity score between the sections in the SectionToSection table
>>> from billsim.bill_similarity import getSimilarBillSections, getBillToBill
>>> from billsim.utils_db import save_bill_to_bill 
>>> s = getSimilarBillSections('116hr200ih')
>>> b2b = getBillToBill(s)
>>> for bill in b2b:
>>>    save_bill_to_bill(b2b[bill]) 
>>>    save_bill_to_bill_sections(b2b[bill]) # This should save the individual sections and the se
"""


def save_bill(
    bill: pymodels.Bill,
    db: Session = SessionLocal()) -> Optional[pymodels.Bill]:
    """
    Save a bill to the database.
    """
    logger.info('Saving bill: {}'.format(bill))
    with db as session:
        billitem = session.query(pymodels.Bill).filter(
            pymodels.Bill.billnumber == bill.billnumber,
            pymodels.Bill.version == bill.version).first()
        if billitem:
            logger.debug('Bill already exists: {}'.format(str(bill)))
            return billitem
        else:
            logger.debug('Saving bill: {}'.format(str(bill)))
        session.add(bill)
        session.flush()
        session.commit()
        logger.debug(
            f'Flush and Commit to save bill {bill.billnumber} {bill.version}')
        bill_saved = session.query(pymodels.Bill).filter(
            pymodels.Bill.billnumber == bill.billnumber,
            pymodels.Bill.version == bill.version).first()
        if bill_saved is None:
            logger.error(
                f'Bill not saved to db: {bill.billnumber} {bill.version}')
            return None
        else:
            return bill_saved


def get_bill_by_billnumber_version(
    billnumber_version: str, db: Session = SessionLocal()
) -> Optional[pymodels.Bill]:
    billnumber_version_dict = getBillnumberversionParts(billnumber_version)
    logger.debug('billnumber_version_dict: {}'.format(
        str(billnumber_version_dict)))
    with db as session:
        bill = db.query(pymodels.Bill).filter(
            pymodels.Bill.billnumber == billnumber_version_dict.get(
                'billnumber'), pymodels.Bill.version ==
            billnumber_version_dict.get('version')).first()
    if bill is None:
        return None
    return bill


def get_bill_ids(
    billnumber_versions: list[str], db: Session = SessionLocal()) -> dict:
    """
    Return a dictionary of bill_id's for the billnumber_versions
     { billnumber_version: bill_id }

    Args:
        billnumber_versions (list[str]): list of billnumber_versions of the form '116hr200ih' 
        db (Session, optional): db session. Defaults to SessionLocal().

    Returns:
        billdict (dict): dictionary of the form { billnumber_version: bill_id }
    """
    billdict = {}
    for billnumber_version in billnumber_versions:
        bill = get_bill_by_billnumber_version(billnumber_version, db)
        if bill:
            billdict[billnumber_version] = bill.id
    return billdict


def get_bill_to_bill(
    bill_id: int, bill_to_id: int,
    db: Session = SessionLocal()) -> Optional[pymodels.BillToBill]:
    """
    Return the BillToBill object for the bill_id and bill_to_id
    """
    with db as session:
        bill_to_bill = session.query(pymodels.BillToBill).filter(
            pymodels.BillToBill.bill_id == bill_id,
            pymodels.BillToBill.bill_to_id == bill_to_id).first()
        if bill_to_bill is None:
            return None
    return bill_to_bill


def get_or_create_sectionitem(section_meta: pymodels.SectionMeta,
                              db: Session = SessionLocal()):
    logger.debug("section_meta: {}".format(section_meta))
    if section_meta.billnumber_version is None:
        return None
    bill = get_bill_by_billnumber_version(section_meta.billnumber_version)
    if bill is None:
        billnumber_version_dict = getBillnumberversionParts(
            section_meta.billnumber_version)
        billnumber = str(billnumber_version_dict.get('billnumber'))
        version = str(billnumber_version_dict.get('version'))
        bill = save_bill(pymodels.Bill(billnumber=billnumber, version=version),
                         db)
    if bill is None:
        return None
    sectionItem = db.query(pymodels.SectionItem).filter(
        pymodels.SectionItem.bill_id == bill.id,
        pymodels.SectionItem.section_id == section_meta.section_id).first()
    if sectionItem is None:
        if section_meta.label is None or section_meta.header is None or section_meta.length is None:
            logger.warning(
                f'Section meta is missing label, header or length: {section_meta}'
            )
        sectionItem = pymodels.SectionItem(bill_id=bill.id,
                                           section_id=section_meta.section_id,
                                           label=section_meta.label,
                                           header=section_meta.header,
                                           length=section_meta.length)
        with db as session:
            session.add(sectionItem)
            session.flush()
            session.commit()
        # NOTE: sectionItem should now have an autogenerated id
        return sectionItem
    else:
        logger.debug('SectionItem already exists')
        return sectionItem


def save_section_to_section(section_meta: pymodels.SectionMeta,
                            similar_section: pymodels.SimilarSection,
                            db: Session = SessionLocal()):
    sectionItem = get_or_create_sectionitem(section_meta, db)
    if sectionItem is None:
        # TODO: raise exception?
        return None
    similar_section_item = get_or_create_sectionitem(
        pymodels.SectionMeta(**dict(similar_section)), db)
    if similar_section_item is None:
        # TODO: raise exception?
        return None
    section_to_section = db.query(pymodels.SectionToSection).filter(
        pymodels.SectionToSection.id == sectionItem.id,
        pymodels.SectionToSection.id_to == similar_section_item.id).first()
    if section_to_section is None:
        section_to_section = pymodels.SectionToSection(
            id=sectionItem.id,
            id_to=similar_section_item.id,
            score_es=similar_section.score_es,
            score=similar_section.score,
            score_to=similar_section.score_to)
        db.add(section_to_section)
    else:
        logger.debug('SectionToSection already exists')
        # Update the scores that we have
        if similar_section.score_es:
            logger.debug('SectionToSection adding/updating score_es')
            setattr(section_to_section, 'score_es', similar_section.score_es)
        if similar_section.score:
            logger.debug('SectionToSection adding/updating score')
            setattr(section_to_section, 'score', similar_section.score)
        if similar_section.score_to:
            logger.debug('SectionToSection adding/updating score_to')
            setattr(section_to_section, 'score_to', similar_section.score_to)
    with db as session:
        session.flush()
        session.commit()
    return section_to_section


def save_section(
    section: pymodels.Section, db: Session = SessionLocal()) -> Optional[int]:
    """
   Get the sectionMeta from the section
   check if a SectionItem row exists for this sectionMeta
   if not, create one
   Then do the same for each similar_section
   Then save the section to section between the from and to
   """
    section_meta = pymodels.SectionMeta(**dict(section))
    section_item = get_or_create_sectionitem(section_meta)
    if not section_item:
        raise Exception(
            'Could not create or get sectionItem from section: {}'.format(
                str(section_meta)))
    for similar_section in section.similar_sections:
        save_section_to_section(section_meta, similar_section, db)


def save_bill_to_bill(bill_to_bill_model: pymodels.BillToBillModel,
                      db: Session = SessionLocal()):
    """
    Save bill to bill join to the database.
    """
    bill = get_bill_by_billnumber_version(bill_to_bill_model.billnumber_version)
    if bill is None:
        logger.warning('No bill found in db for {}'.format(
            bill_to_bill_model.billnumber_version))
        try:
            billnumber_version_dict = getBillnumberversionParts(
                bill_to_bill_model.billnumber_version)
            billnumber = str(billnumber_version_dict.get('billnumber'))
            version = str(billnumber_version_dict.get('version'))
        except:
            logger.error(
                'Billnumber version not of the correct form: {}'.format(
                    bill_to_bill_model.billnumber_version))
            return

        bill = save_bill(
            pymodels.Bill(billnumber=billnumber,
                          version=version,
                          length=bill_to_bill_model.length))

    bill_to = get_bill_by_billnumber_version(
        bill_to_bill_model.billnumber_version_to)
    if bill_to is None:
        err_msg = 'No bill found in db for {}'.format(
            bill_to_bill_model.billnumber_version_to)
        logger.warning(err_msg)
        try:
            billnumber_version_to_dict = getBillnumberversionParts(
                bill_to_bill_model.billnumber_version_to)
        except:
            logger.error(
                'Billnumber version (to bill) not of the correct form: {}'.
                format(bill_to_bill_model.billnumber_version_to))
            return
        billnumber_to = str(billnumber_version_to_dict.get('billnumber'))
        version_to = str(billnumber_version_to_dict.get('version'))
        length_to = getBillLength(bill_to_bill_model.billnumber_version_to)
        bill_to = save_bill(
            pymodels.Bill(billnumber=billnumber_to,
                          version=version_to,
                          length=length_to))
    if bill is None or bill_to is None:
        raise Exception(
            'Could not create bill item for one or both of: {0}, {1}.'.format(
                bill_to_bill_model.billnumber_version,
                bill_to_bill_model.billnumber_version_to))
    #sections = json.dumps(bill_to_bill_model.sections)
    logger.debug('Saving bill to bill join: {0} & {1}'.format(
        bill.id, bill_to.id))
    if bill.id and bill_to.id:
        bill_to_bill = get_bill_to_bill(bill_id=bill.id, bill_to_id=bill_to.id)
    else:
        raise Exception('No bill id found for one or both of: {0}, {1}.'.format(
            bill_to_bill_model.billnumber_version,
            bill_to_bill_model.billnumber_version_to))

    bill_to_bill_new = pymodels.BillToBill(
        bill_id=bill.id,
        bill_to_id=bill_to.id,
        score_es=bill_to_bill_model.score_es,
        score=bill_to_bill_model.score,
        score_to=bill_to_bill_model.score_to,
        reasonsstring=bill_to_bill_model.reasonsstring,
        identified_by=bill_to_bill_model.identified_by,
        sections_num=bill_to_bill_model.sections_num,
        sections_match=bill_to_bill_model.sections_match)
    if bill_to_bill is None:
        logger.debug(
            "********** NO Bill-to-bill yet for: {0}, {1} ********".format(
                bill.id, bill_to.id))
        with db as session:
            session.add(bill_to_bill_new)
            session.flush()
            session.commit()
    else:
        logger.debug("********** UPDATING BILLS: {0}, {1} ********".format(
            bill.id, bill_to.id))
        # Use the passed-in values if they exist, otherwise use the values from the db
        if bill_to_bill_new.score_es:
            logger.debug("********* UPDATING score_es")
            setattr(bill_to_bill, 'score_es', bill_to_bill_new.score_es)

        if bill_to_bill_new.score:
            logger.debug("********* UPDATING score")
            setattr(bill_to_bill, 'score', bill_to_bill_new.score)

        if bill_to_bill_new.score_to:
            logger.debug("********* UPDATING score_to")
            setattr(bill_to_bill, 'score_to', bill_to_bill_new.score_to)

        if bill_to_bill_new.reasonsstring:
            logger.debug("********* UPDATING reasonsstring:")
            if not bill_to_bill.reasonsstring:
                setattr(bill_to_bill, 'reasonsstring',
                        bill_to_bill_new.reasonsstring)
                reasonsstring = bill_to_bill_new.reasonsstring
            else:
                reasonsstring = ", ".join(
                    list(
                        set([
                            reason.strip()
                            for reason in bill_to_bill.reasonsstring.split(',')
                        ] + [
                            reason.strip() for reason in
                            bill_to_bill_new.reasonsstring.split(',')
                        ])))
                setattr(bill_to_bill, 'reasonsstring', reasonsstring)
            logger.debug(reasonsstring)

        if bill_to_bill_new.identified_by:
            logger.debug("********* UPDATING identified_by")
            setattr(bill_to_bill, 'identified_by',
                    bill_to_bill_new.identified_by)

        if bill_to_bill_new.sections_num:
            logger.debug("********* UPDATING sections_num")
            setattr(bill_to_bill, 'sections_num', bill_to_bill_new.sections_num)

        if bill_to_bill_new.sections_match:
            logger.debug("********* UPDATING sections_match")
            setattr(bill_to_bill, 'sections_match',
                    bill_to_bill_new.sections_match)
        with db as session:
            session.add(bill_to_bill)
            session.flush()
            session.commit()


def save_bill_to_bill_sections(bill_to_bill_model: pymodels.BillToBillModel,
                               db: Session = SessionLocal()):
    """
    For each bill to bill, save the 'sections' object, which includes the sections of the 'from'
    bill in order, along with the top similar section of the 'to' bill.
    """
    sections = bill_to_bill_model.sections
    if sections is None:
        return None
    for section in sections:
        save_section(section, db)


def save_bill_and_sections(billPath: pymodels.BillPath,
                           replace=False) -> pymodels.Status:
    """
    Parse bill (from path) and save it, and its sections to the Bill and SectionItem
    tables, respectively.
    The same as saving bill and sections within elastic_load.indexBill
    Args:
        billPath (pymodels.BillPath): absolute path to the bill XML 
        replace (bool, optional): replace the bill or section if it already exists. Defaults to False.

    Returns:
        pymodels.Status: status of save to db, of the form {success: True/False, message: 'message'}} 
    """
    status = pymodels.Status(
        success=True, message=f'Indexed bill: {billPath.billnumber_version};')

    try:
        billTree = etree.parse(billPath.filePath, parser=etree.XMLParser())
    except Exception as e:
        logger.error('Exception: '.format(e))
        raise Exception('Could not parse bill: {}'.format(billPath.filePath))
    length = getBillLengthbyPath(billPath.filePath)
    defaultNS = getDefaultNamespace(billTree)
    if defaultNS and defaultNS == constants.NAMESPACE_USLM2:
        logger.debug('Parsing bill WITH USLM2')
        logger.debug('defaultNS: {}'.format(defaultNS))
        sections = billTree.xpath('//uslm:section',
                                  namespaces={'uslm': defaultNS})
    else:
        logger.debug('NO NAMESPACE')

        sections = billTree.xpath('//section')

    billmatch = constants.BILL_NUMBER_REGEX_COMPILED.match(
        billPath.billnumber_version)
    billversion = ''
    billnumber = ''
    if billmatch:
        billmatch_dict = billmatch.groupdict()
        billnumber = '{congress}{stage}{number}'.format(**billmatch_dict)
        billversion = billmatch_dict.get('version', '')
    try:
        bill = pymodels.Bill(billnumber=billnumber,
                             version=billversion,
                             length=length)
        savedbill = save_bill(bill)
        if savedbill:
            status.message = status.message + f'; id={bill.id}'
        else:
            status.success = False
            status.message = status.message + f'; Could not save bill'
            return status
    except Exception as e:
        logger.error('Could not add bill to database: {}'.format(e))
        status.success = False
        status.message = 'Could not add bill to database: {}'.format(e)

    sectionData = [{
        'section_id':
            getId(section),
        'section_number':
            getEnum(section, defaultNS),
        'section_text':
            etree.tostring(section, method="text", encoding="unicode"),
        'section_length':
            len(etree.tostring(section, method="text", encoding="unicode")),
    } for section in sections]
    try:
        # Add sectionItems to db here
        for sectionDataItem in sectionData:
            if sectionDataItem.get('section_id') is None:
                continue
            try:
                section_meta = pymodels.SectionMeta(
                    billnumber_version=f'{billnumber}{billversion}',
                    section_id=sectionDataItem.get('section_id'),
                    label=sectionDataItem.get('section_number', ''),
                    length=sectionDataItem.get('length', 0))
                get_or_create_sectionitem(section_meta)
            except Exception as e:
                logger.error(
                    f'Could not add section in {billnumber}{billversion} to database: {e}'
                )
                logger.error(f'{sectionDataItem}')
        status.message = status.message + f'; saved {len(sectionData)} sections'
    except Exception as e:
        logger.error('Could not add sections to database: {}'.format(e))
        status.success = False
        status.message = f'Failed to index sections for : {billPath.billnumber_version}; {e}'
    return status