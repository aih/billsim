#!/usr/bin/env python3

import sys
import logging
from typing import Optional
from urllib.parse import _NetlocResultMixinStr
from lxml import etree
from sqlalchemy import tuple_, delete
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from billsim.utils import getDefaultNamespace, getBillLength, getBillLengthbyPath, getBillnumberversionParts, getId, getEnum, getSections, parseFilePath
from billsim.database import SessionLocal
from billsim import pymodels, constants
from datetime import datetime

logger = logging.getLogger(constants.LOGGER_NAME)
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


def create_currency(
    version: str,
    db: Session = SessionLocal()) -> Optional[int]:
    new_currency = pymodels.CurrencyModel(version=version, date=datetime.utcnow())
    with db as session:
        session.add(new_currency)
        session.flush()
        session.commit()
        session.refresh(new_currency)
    return new_currency.currency_id

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

def save_sections(
    section_models,
    db: Session = SessionLocal()):
    logger.info("Saving sections")
    section_dicts = [i.__dict__ for i in section_models]
    insert_stmt = insert(pymodels.SectionItem)
    do_update_stmt = insert_stmt.on_conflict_do_nothing(
        constraint='billnumber_version_section_id')
    with db as session:
        session.execute(do_update_stmt, section_dicts)
        session.commit()


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


def batch_get_bill_ids(billnumber_versions: list, db: Session = SessionLocal()) -> dict:
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
    split_number_versions = []
    for billnumber_version in billnumber_versions:
        billdict[billnumber_version] = None
        billnumber_version_dict = getBillnumberversionParts(billnumber_version)
        billnumber = str(billnumber_version_dict.get('billnumber'))
        version = str(billnumber_version_dict.get('version'))
        split_number_versions.append((billnumber, version))

    with db as session:
        query = session.query(pymodels.Bill.id, pymodels.Bill.billnumber, pymodels.Bill.version).filter(
            tuple_(pymodels.Bill.billnumber, pymodels.Bill.version).in_(split_number_versions)
        )
        results = query.all()

    for result in results:
        billdict[f'{result[1]}{result[2]}'] = result.id
        
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


def batch_get_section_ids(s2s_models: list[pymodels.SectionToSectionModel], db: Session = SessionLocal()) -> dict:
    """
    Return a dictionary from billnumber and section id attribute to (bill_id, section id)

    Args:
        s2s_models (list[]): list of SectionToSectionModel
        db (Session, optional): db session. Defaults to SessionLocal().

    Returns:
        sectiondict (dict)
    """
    sections_set = set()
    sectiondict = {}
    for model in s2s_models:
        sections_set.add((model.bill_number, model.section_id))
        sections_set.add((model.bill_number_to, model.section_to_id))

    with db as session:
        query = session.query(pymodels.SectionItem.id, pymodels.SectionItem.bill_id, pymodels.SectionItem.billnumber_version, pymodels.SectionItem.section_id_attr).filter(
            tuple_(pymodels.SectionItem.billnumber_version, pymodels.SectionItem.section_id_attr).in_(sections_set)
        )
        results = query.all()

    for result in results:
        logger.debug('result for section id query: {}'.format(result))

        billname = result[2]
        section_attr = result[3]
        if (billname not in sectiondict):
            sectiondict[billname] = {}
        sectiondict[billname][section_attr] = (result[0], result[1])
        
    return sectiondict

def batch_save_section_to_section(s2s_models: list[pymodels.SectionToSectionModel], db: Session = SessionLocal()):
    sectiondict = batch_get_section_ids(s2s_models)
    section_to_sections = []
    for model in s2s_models:
        logger.debug('sectiontosection model: {}'.format(model))
        from_ids = sectiondict[model.bill_number][model.section_id]
        to_ids = sectiondict[model.bill_number_to][model.section_to_id]
        section_to_sections.append({
            'bill_id': from_ids[1],
            'bill_to_id': to_ids[1],
            'section_id': from_ids[0],
            'section_to_id': to_ids[0],
            'score': model.score,
            'currency_id': model.currency_id
        })

    insert_stmt = insert(pymodels.SectionToSection).values(section_to_sections)
    update_values = { 
        'score': insert_stmt.excluded.score, 
        'currency_id': insert_stmt.excluded.currency_id
    }
    do_update_stmt = insert_stmt.on_conflict_do_update(
        constraint='sectiontosection_pkey',
        set_= update_values
    )
    with db as session:
        session.execute(do_update_stmt)
        session.commit()

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

    reasonsstring = ""
    if bill_to_bill_model.reasons:
        reasonsstring = ", ".join(bill_to_bill_model.reasons)
    bill_to_bill_new = pymodels.BillToBill(
        bill_id=bill.id,
        bill_to_id=bill_to.id,
        score_es=bill_to_bill_model.score_es,
        score=bill_to_bill_model.score,
        score_to=bill_to_bill_model.score_to,
        reasonsstring=reasonsstring,
        identified_by=bill_to_bill_model.identified_by,
        sections_num=bill_to_bill_model.sections_num,
        sections_match=bill_to_bill_model.sections_match,
        currency_id=bill_to_bill_model.currency_id)
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

def batch_save_bill_to_bill(b2b_models: [pymodels.BillToBillModel],
                      db: Session = SessionLocal()):
    """
    Save bill to bill join to the database.
    Requires a list of BillToBillModel objects with bill_id and bill_to_id set.
    """

    # Backfill the bill to bill models with bill DB ids before saving.
    # If we pass in bill to bill models with bill DB ids already set,
    # this is unnecessary, but we'll do it anyway for simplicity.
    billnumber_versions_to_query = []
    for model in b2b_models:
        billnumber_versions_to_query.append(model.billnumber_version)
        billnumber_versions_to_query.append(model.billnumber_version_to)

    billnumber_version_id_dict = batch_get_bill_ids(billnumber_versions_to_query)

    # TODO: remove
    # This seems duplicative and unnecessary; if the bill is missing from the db
    # we add it below
    #for billnum in billnumber_version_id_dict:
    #    # The caller should ensure all bills are saved in the bill table before using this
    #    # method.
    #    if billnumber_version_id_dict[billnum] is None:
    #        #raise ValueError(f"Bill numberversion not found in the database: {billnum}")

    for model in b2b_models:
        # billnumber, version, billnumber_to, version_to
        model.bill_id = billnumber_version_id_dict.get(model.billnumber_version)
        if model.bill_id is None:
            bill = save_bill(pymodels.Bill(billnumber=model.billnumber, version=model.version))
            if bill is None:
                raise ValueError('Could not save bill: {0}'.format(model.billnumber_version))
            model.bill_id = bill.id

        model.bill_to_id = billnumber_version_id_dict[model.billnumber_version_to]
        if model.bill_id is None:
            bill_to = save_bill(pymodels.Bill(billnumber=model.billnumber_to, version=model.version_to))
            if bill_to is None:
                raise ValueError('Could not save bill_to: {0}'.format(model.billnumber_version_to))
            model.bill_to_id = bill_to.id

    bill_to_bills = []
    for model in b2b_models:

        bill_to_bills.append({
            'bill_id': model.bill_id,
            'bill_to_id': model.bill_to_id,
            'score': model.score,
            'score_to': model.score_to,
            'reasonsstring': ','.join(model.reasons),
            'sections_num': model.sections_num,
            'sections_match': model.sections_match,
            'currency_id': model.currency_id
        })

    insert_stmt = insert(pymodels.BillToBill).values(bill_to_bills)
    update_values = { 
        'score': insert_stmt.excluded.score, 
        'score_to': insert_stmt.excluded.score_to, 
        'reasonsstring': insert_stmt.excluded.reasonsstring, 
        'sections_match': insert_stmt.excluded.sections_match, 
        'sections_num': insert_stmt.excluded.sections_num,
        'currency_id': insert_stmt.excluded.currency_id
    }
    do_update_stmt = insert_stmt.on_conflict_do_update(
        constraint='billtobill_pkey',
        set_= update_values
    )
    with db as session:
        session.execute(do_update_stmt)
        session.commit()

def cleanup_old_bill_to_bill(current_currency_id, db: Session = SessionLocal()):
    delete_stmt = delete(pymodels.BillToBill).where(pymodels.BillToBill.currency_id<current_currency_id)
    with db as session:
        session.execute(delete_stmt)
        session.commit()

def cleanup_old_section_to_section(current_currency_id, db: Session = SessionLocal()):
    delete_stmt = delete(pymodels.SectionToSection).where(pymodels.SectionToSection.currency_id<current_currency_id)
    with db as session:
        session.execute(delete_stmt)
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

    billTree = parseFilePath(billPath.filePath)
    length = getBillLengthbyPath(billPath.filePath)
    defaultNS = getDefaultNamespace(billTree)
    if defaultNS and defaultNS == constants.NAMESPACE_USLM2:
        logger.debug('Parsing bill WITH USLM2')
        logger.debug('defaultNS: {}'.format(defaultNS))
    else:
        logger.debug('NO NAMESPACE')
    sections = getSections(billTree, defaultNS)

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
