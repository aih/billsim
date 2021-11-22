#!/usr/bin/env python3

import sys
import logging
from sqlalchemy.orm import Session
from billsim.database import SessionLocal
from billsim import pymodels

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def save_bill(bill: pymodels.Bill, db: Session = SessionLocal()):
    """
    Save a bill to the database.
    """
    billid = None
    with db as session:
        session.add(bill)
        session.commit()
        bill_saved = session.query(
            pymodels.Bill).filter(pymodels.Bill.billnumber_version ==
                                  bill.billnumber_version).first()
        if bill_saved is not None:
            billid = bill_saved.id
    return billid


def get_bill_by_billnumber_version(
    billnumber_version: str, db: Session = SessionLocal()) -> pymodels.Bill:
    # TODO test billnumber_version format
    bill = db.query(pymodels.Bill).filter(
        pymodels.Bill.billnumber_version == billnumber_version).first()
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
        logger.error(e)
        bill_id = save_bill(
            pymodels.Bill(
                billnumber_version=bill_to_bill_model.billnumber_version,
                length=bill_to_bill_model.length))

    try:
        bill_to = get_bill_by_billnumber_version(
            bill_to_bill_model.billnumber_version_to)
        bill_to_id = bill_to.id
    except Exception as e:
        logger.error('No bill found in db for {}'.format(
            bill_to_bill_model.billnumber_version_to))
        logger.error(e)
        bill_to_id = save_bill(
            pymodels.Bill(
                billnumber_version=bill_to_bill_model.billnumber_version))
    if bill_id is None or bill_to_id is None:
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
        identified_by=bill_to_bill_model.identified_by)
    with db as session:
        session.add(bill_to_bill)
        session.commit()