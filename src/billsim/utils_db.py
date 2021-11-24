#!/usr/bin/env python3

import sys
import logging
from sqlalchemy.orm import Session
from billsim.utils import getBillLength
from billsim.database import SessionLocal
from billsim import pymodels, constants
from billsim

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(level='INFO')



def save_bill(bill: pymodels.Bill, db: Session = SessionLocal()):
    """
    Save a bill to the database.
    """
    billid = None
    with db as session:
        session.add(bill)
        session.commit()
        bill_saved = session.query(pymodels.Bill).filter(
            pymodels.Bill.billnumber == bill.billnumber,
            pymodels.Bill.version == bill.version).first()
        if bill_saved is not None:
            billid = bill_saved.id
    return billid


def get_bill_by_billnumber_version(
    billnumber_version: str, db: Session = SessionLocal()) -> pymodels.Bill:
    billnumber_version_dict = getBillnumberversionParts(billnumber_version)
    logger.debug('billnumber_version_dict: {}'.format(
        str(billnumber_version_dict)))
    bill = db.query(pymodels.Bill).filter(
        pymodels.Bill.billnumber == billnumber_version_dict.get('billnumber'),
        pymodels.Bill.version == billnumber_version_dict.get(
            'version')).first()
    if bill is None:
        raise ValueError('Bill not found')
    return bill


def save_bill_to_bill(bill_to_bill_model: pymodels.BillToBillModel,
                      db: Session = SessionLocal()):
    """
    Save bill to bill join to the database.
    """
    try:
        bill = get_bill_by_billnumber_version(
            bill_to_bill_model.billnumber_version)
        bill_id = bill.id
    except Exception as e:
        logger.error('No bill found in db for {}'.format(
            bill_to_bill_model.billnumber_version))
        logger.error('Error: {}'.format(e))
        try:
            billnumber_version_dict = getBillnumberversionParts(
                bill_to_bill_model.billnumber_version)
        except:
            logger.error(
                'Billnumber version not of the correct form: {}'.format(
                    bill_to_bill_model.billnumber_version))
            return
        billnumber = str(billnumber_version_dict.get('billnumber'))
        version = str(billnumber_version_dict.get('version'))

        bill_id = save_bill(
            pymodels.Bill(billnumber=billnumber,
                          version=version,
                          length=bill_to_bill_model.length))

    try:
        bill_to = get_bill_by_billnumber_version(
            bill_to_bill_model.billnumber_version_to)
        bill_to_id = bill_to.id
    except Exception as e:
        logger.error('No bill found in db for {}'.format(
            bill_to_bill_model.billnumber_version_to))
        logger.error('Error: {}'.format(e))
        try:
            billnumber_version_to_dict = getBillnumberversionParts(
                bill_to_bill_model.billnumber_version_to)
        except:
            logger.error(
                'Billnumber version (to bill) not of the correct form: {}'.
                format(bill_to_bill_model.billnumber_version_to))
            return
        billnumber = str(billnumber_version_to_dict.get('billnumber'))
        version = str(billnumber_version_to_dict.get('version'))
        length = getBillLength(bill_to_bill_model.billnumber_version_to)
        bill_to_id = save_bill(
            pymodels.Bill(billnumber=billnumber, version=version,
                          length=length))
    if bill_id is None or bill_to_id is None:
        logger.error('bill_id: {}'.format(bill_id))
        logger.error('bill_to_id: {}'.format(bill_to_id))
        raise Exception(
            'Could not create bill item for one or both of: {0}, {1}.'.format(
                bill_to_bill_model.billnumber_version,
                bill_to_bill_model.billnumber_version_to))
    #sections = json.dumps(bill_to_bill_model.sections)
    logger.info('Saving bill to bill join: {0} & {1}'.format(
        bill_id, bill_to_id))
    bill_to_bill = pymodels.BillToBillLite(
        bill_id=bill_id,
        bill_to_id=bill_to_id,
        score_es=bill_to_bill_model.score_es,
        score=bill_to_bill_model.score,
        score_to=bill_to_bill_model.score_to,
        reasons=bill_to_bill_model.reasons,
        identified_by=bill_to_bill_model.identified_by,
        sections_num=bill_to_bill_model.sections_num,
        sections_matched=bill_to_bill_model.sections_match)
    with db as session:
        session.add(bill_to_bill)
        session.commit()