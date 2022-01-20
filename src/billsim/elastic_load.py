#!/usr/bin/env python3

import re
import json
import logging
import sys
from billsim.utils_db import get_or_create_sectionitem, save_bill
from lxml import etree
from elasticsearch import exceptions, Elasticsearch
from collections import OrderedDict

es = Elasticsearch()
from billsim import constants
from billsim.utils import getBillnumberversionParts, getBillXmlPaths, getBillLengthbyPath, getDefaultNamespace, getId, getHeader, getEnum, getText
from billsim.utils_es import getBill_es
from billsim.pymodels import SectionMeta, Status, BillPath, Bill, SectionItem

logging.basicConfig(filename='elastic_load.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def getMapping(map_path: str) -> dict:
    with open(map_path, 'r') as f:
        return json.load(f)


# For future possible improvements, see https://www.is.inf.uni-due.de/bib/pdf/ir/Abolhassani_Fuhr_04.pdf
# Applying the Divergence From Randomness Approach for Content-Only Search in XML Documents
def createIndex(index: str = constants.INDEX_SECTIONS,
                body: dict = constants.BILLSECTION_MAPPING,
                delete=False):
    if delete:
        try:
            es.indices.delete(index=index)
        except exceptions.NotFoundError:
            logger.error('No index to delete: {0}'.format(index))

    logger.info('Creating index with mapping: ')
    logger.info(str(body))
    es.indices.create(index=index, ignore=400, body=body)


def indexBill(billPath: BillPath,
              index_types: dict = {'sections': constants.INDEX_SECTIONS},
              reindex=True,
              withDb=False) -> Status:
    """
  Index bill with Elasticsearch

  Args:
      bill_path (str): location of the bill xml file.
      billnumber_version (str): bill number and version, of the form 117hr200ih.
      index_types (dict, optional): Index by 'sections', 'bill_full' or both. Defaults to ['sections'].
      reindex (bool, optional): Whether to reindex the bill if it already is in ES. Defaults to True.
      withDb (bool, optional): Whether to save the bill and sections to the database. Defaults to False.

  Raises:
      Exception: Could not parse bill xml file. 

  Returns:
      Status: status of the indexing of the form {success: True/False, message: 'message'}} 
  """
    if not reindex:
        bnv = getBillnumberversionParts(billPath.billnumber_version)
        for index in index_types:
            billres = getBill_es(bnv.get('billnumber', ''),
                                 bnv.get('version', ''), index)
            if billres:
                return Status(success=False, message='Bill already indexed')

    try:
        billTree = etree.parse(billPath.filePath, parser=etree.XMLParser())
    except Exception as e:
        logger.error('Exception: '.format(e))
        raise Exception('Could not parse bill: {}'.format(billPath.filePath))
    length = getBillLengthbyPath(billPath.filePath)
    dublinCore = None
    defaultNS = getDefaultNamespace(billTree)
    if defaultNS and defaultNS == constants.NAMESPACE_USLM2:
        logger.debug('INDEXING WITH USLM2')
        logger.debug('defaultNS: {}'.format(defaultNS))
        dcdate = getText(
            billTree.xpath('//uslm:meta/dc:date',
                           namespaces={
                               'uslm': defaultNS,
                               'dc': constants.NAMESPACE_DC
                           }))
        congress = billTree.xpath('//uslm:meta/uslm:congress',
                                  namespaces={'uslm': defaultNS})
        congress_text = re.sub(r'[a-zA-Z ]+$', '', getText(congress))
        session = billTree.xpath('//uslm:meta/uslm:session',
                                 namespaces={'uslm': defaultNS})
        session_text = re.sub(r'[a-zA-Z ]+$', '', getText(session))
        dc_type = billTree.xpath('//uslm:preface/dc:type',
                                 namespaces={
                                     'uslm': defaultNS,
                                     'dc': constants.NAMESPACE_DC
                                 })
        docNumber = billTree.xpath('//uslm:preface/uslm:docNumber',
                                   namespaces={
                                       'uslm': defaultNS,
                                       'dc': constants.NAMESPACE_DC
                                   })
        if dc_type and docNumber:
            legisnum_text = getText(dc_type) + ' ' + getText(docNumber)
        else:
            legisnum_text = ''

        dctitle = getText(
            billTree.xpath('//uslm:meta/dc:title',
                           namespaces={
                               'uslm': defaultNS,
                               'dc': constants.NAMESPACE_DC
                           })),
        sections = billTree.xpath(
            '//uslm:section[not(ancestor::uslm:section) and not(@status="withdrawn")]',
            namespaces={'uslm': defaultNS})
        headers = billTree.xpath('//uslm:heading',
                                 namespaces={'uslm': defaultNS})
    else:
        logger.debug('NO NAMESPACE')
        dublinCores = billTree.xpath('//dublinCore')
        if (dublinCores is not None) and (len(dublinCores) > 0):
            dublinCore = etree.tostring(dublinCores[0],
                                        method="xml",
                                        encoding="unicode"),
        else:
            dublinCore = ''
        dcdate = getText(
            billTree.xpath('//dublinCore/dc:date',
                           namespaces={'dc': constants.NAMESPACE_DC}))
        # TODO find date for enr bills in the bill status (for the flat congress directory structure)
        if (dcdate is None
                or len(dcdate) == 0) and '/data.xml' in billPath.filePath:
            metadata_path = billPath.filePath.replace('/data.xml', '/data.json')
            try:
                with open(metadata_path, 'rb') as f:
                    metadata = json.load(f)
                    dcdate = metadata.get('issued_on', None)
            except:
                pass
        if dcdate is None or len(dcdate) == 0:
            dcdate = None

        congress = billTree.xpath('//form/congress')
        congress_text = re.sub(r'[a-zA-Z ]+$', '', getText(congress))
        session = billTree.xpath('//form/session')
        session_text = re.sub(r'[a-zA-Z ]+$', '', getText(session))
        legisnum = billTree.xpath('//legis-num')
        legisnum_text = getText(legisnum)
        dctitle = getText(
            billTree.xpath('//dublinCore/dc:title',
                           namespaces={'dc': constants.NAMESPACE_DC}))
        sections = billTree.xpath(
            '//section[not(ancestor::section) and not(@status="withdrawn")]'),
        headers = billTree.xpath('//header')

    billmatch = constants.BILL_NUMBER_REGEX_COMPILED.match(
        billPath.billnumber_version)
    billversion = ''
    billnumber = ''
    if billmatch:
        billmatch_dict = billmatch.groupdict()
        billnumber = '{congress}{stage}{number}'.format(**billmatch_dict)
        billversion = billmatch_dict.get('version', '')
    headers_text = [header.text for header in headers]

    if withDb:
        try:
            bill = Bill(billnumber=billnumber,
                        version=billversion,
                        length=length)
            save_bill(bill)
        except Exception as e:
            logger.error('Could not add bill to database: {}'.format(e))
    res = {}

    # Uses an OrderedDict to deduplicate headers
    # TODO handle missing header and enum separately
    if 'sections' in index_types.keys():
        sectionData = [{
            'section_id':
                getId(section),
            'section_number':
                getEnum(section, defaultNS),
            'section_header':
                getHeader(section, defaultNS),
            'section_text':
                etree.tostring(section, method="text", encoding="unicode"),
            'section_length':
                len(etree.tostring(section, method="text", encoding="unicode")),
            'section_xml':
                etree.tostring(section, method="xml", encoding="unicode")
        } for section in sections]

        if withDb:
            try:
                # Add sectionItems to db here
                for sectionDataItem in sectionData:
                    if sectionDataItem.get('section_id') is None:
                        continue
                    try:
                        section_meta = SectionMeta(
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
            except Exception as e:
                logger.error('Could not add sections to database: {}'.format(e))

        doc = {
            'id': billPath.billnumber_version,
            'congress': congress_text,
            'session': session_text,
            'length': length,
            'dctitle': dctitle,
            'date': dcdate,
            'legisnum': legisnum_text,
            'billnumber': billnumber,
            'billversion': billversion,
            'headers': list(OrderedDict.fromkeys(headers_text)),
            'sections_num': len(sections),
            'sections': sectionData
        }
        if dublinCore:
            doc['dublinCore'] = dublinCore

        res = es.index(index=index_types['sections'],
                       body=doc,
                       id=billPath.billnumber_version)

    if 'bill_full' in index_types.keys():
        billText = etree.tostring(billTree, method="text", encoding="unicode")
        doc_full = {
            'id': billPath.billnumber_version,
            'congress': congress_text,
            'session': session_text,
            'length': length,
            'sections_num': len(sections),
            'dc': dublinCore,
            'dctitle': dctitle,
            'date': dcdate,
            'legisnum': legisnum_text,
            'billnumber': billnumber,
            'billversion': billversion,
            'headers': list(OrderedDict.fromkeys(headers_text)),
            'billtext': billText
        }
        res = es.index(index=index_types['bill_full'],
                       body=doc_full,
                       id=billPath.billnumber_version)

    # TODO: handle processing of bill section index separately from full bill
    result_status = res.get('result', None)
    if result_status == 'created' or result_status == 'updated':
        return Status(
            success=True,
            message=
            f'Indexed ({result_status}) bill: {billPath.billnumber_version}')
    else:
        return Status(
            success=False,
            message=f'Failed to index bill: {billPath.billnumber_version}')

    # billRoot = billTree.getroot()
    # nsmap = {k if k is not None else '':v for k,v in billRoot.nsmap.items()}


def initializeBillSectionsIndex(delete_index=False):
    """
  Initializes the index for the congress directory. The 'id' field is set to the billnumber_version and is unique.
  """

    createIndex(delete=delete_index)
    billPaths = getBillXmlPaths()
    logger.info('Indexing {0} bills'.format(len(billPaths)))
    for billPath in billPaths:
        try:
            logger.debug(indexBill(billPath))
        except Exception as e:
            logger.error('Failed to index bill {0}'.format(
                billPath.billnumber_version))
            logger.error(e)


def updateBillSectionsIndex():
    """
    Updates the bill sections index. Finds all bills, checks whether a bill is already in the index, and indexes it if it is not.
    """
    billPaths = getBillXmlPaths()
    logger.info('Found {0} total bills'.format(len(billPaths)))
    for billPath in billPaths:
        try:
            logger.debug(indexBill(billPath))
        except Exception as e:
            logger.error('Failed to index bill {0}'.format(
                billPath.billnumber_version))
            logger.error(e)