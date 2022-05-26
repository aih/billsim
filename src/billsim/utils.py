#!/usr/bin/env python3

from functools import reduce
import os, sys
import re
import logging
from typing import List
from lxml import etree
from xml.etree import ElementTree

from billsim.constants import LOGGER_NAME, PATHTYPE_DEFAULT, PATHTYPE_OBJ, CURRENT_CONGRESS, PATH_TO_CONGRESSDATA_DIR, CONGRESS_DIRS, BILL_NUMBER_PART_REGEX_COMPILED
from billsim.pymodels import BillPath

import traceback

#logging.basicConfig(filename='utils.log', filemode='w', level='INFO')
logger = logging.getLogger(LOGGER_NAME)
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_traceback(e):
    lines = traceback.format_exception(type(e), e, e.__traceback__)
    return ''.join(lines)


def deep_get(d, keys, default=None):
    """
    Example:
        d = {'meta': {'status': 'OK', 'status_code': 200, 'messages': ['first', 'second']}}
        deep_get(d, ['meta', 'status_code'])          # => 200
        deep_get(d, ['meta', 'messages', 0]) == 'first')
        deep_get(d, ['garbage', 'status_code'])       # => None
        deep_get(d, ['meta', 'garbage'], default='-') # => '-'
    """
    assert type(keys) is list
    if d is None:
        return default
    if not keys:
        return d
    if type(d) is list and type(keys[0]) is int:
        return deep_get(d[keys[0]], keys[1:], default)
    return deep_get(d.get(keys[0]), keys[1:], default)


def parseFilePath(filePath):
    try:
        return etree.parse(filePath, parser=etree.XMLParser())
    except Exception as e:
        logger.error('Exception: '.format(e))
        raise Exception('Could not parse bill: {}'.format(filePath))


def getText(item) -> str:
    if item is None:
        return ''

    try:
        if isinstance(item, list):
            item = item[0]
        return item.text
    except:
        return ''


def getId(section) -> str:
    return section.get('id', '')


# NOTE: USLM uses 'num', bill dtd uses 'enum'
def getEnum(section, defaultNS=None) -> str:
    if defaultNS is not None and len(defaultNS) > 0:
        enumpath = section.xpath('ns:enum | ns:num',
                                 namespaces={'ns': defaultNS})
    else:
        enumpath = section.xpath('enum | num')
    if enumpath is not None and len(
            enumpath) > 0 and enumpath[0].text is not None:
        return enumpath[0].text.strip()
    return ''


# NOTE: USLM uses 'heading', bill dtd uses 'header'
def getHeader(section, defaultNS=None) -> str:
    if defaultNS is not None and len(defaultNS) > 0:
        headerpath = section.xpath('ns:header | ns:heading',
                                   namespaces={'ns': defaultNS})
    else:
        headerpath = section.xpath('header | heading')
    if headerpath is not None and len(
            headerpath) > 0 and headerpath[0].text is not None:
        return headerpath[0].text.strip()
    return ''


def getSections(billTree, namespace=None) -> List:
    if namespace is not None and len(namespace) > 0:
        sections = billTree.xpath(
            '//ns:section[not(ancestor::ns:section) and not(@status="withdrawn")]',
            namespaces={'ns': namespace})
    else:
        sections = billTree.xpath(
            '//section[not(ancestor::section) and not(@status="withdrawn")]')
    return sections


def getBillnumberversionParts(billnumber_version: str) -> dict:
    """
    Split a billnumber_version string into its parts.

    Args:
        billnumber_version (str): billnumber_version string of the form '117hr2222enr' 

    Raises:
        ValueError: if the billnumber_version does not match the BILL_NUMBER_PART_REGEX_COMPILED format.

    Returns:
        dict: {'billnumber': xxx, 'version': xxx}} 
    """
    billmatch = BILL_NUMBER_PART_REGEX_COMPILED.match(billnumber_version)
    if billmatch is None:
        raise ValueError(
            'Billnumber version not of the correct form: {}'.format(
                billnumber_version))
    else:
        billmatch_dict = billmatch.groupdict()
        version = billmatch_dict.get('version', '')
        if not version or version.lower() == 'none':
            version = 'ih'
        return {
            'billnumber': '{congress}{stage}{number}'.format(**billmatch_dict),
            'version': version
        }


def billNumberVersionToBillPath(billnumber_version: str,
                                pathType: str = PATHTYPE_DEFAULT) -> BillPath:
    billxmlpath = CONGRESS_DIRS[pathType]["billNumberVersionToPath"](
        billnumber_version)
    logger.debug(
        'PATH_TO_CONGRESSDATA_DIR: {0}'.format(PATH_TO_CONGRESSDATA_DIR))
    logger.debug('billpath: {0}'.format(billxmlpath))
    fileName = os.path.basename(billxmlpath)
    billxmlpath_abs = os.path.join(PATH_TO_CONGRESSDATA_DIR,
                                   re.sub(r'^\/?(data)?\/', r'', billxmlpath))
    logger.debug('Absolute bill path: {0}'.format(billxmlpath_abs))
    return BillPath(filePath=billxmlpath_abs,
                    fileName=fileName,
                    billnumber_version=billnumber_version)


def getBillLengthbyPath(filePath: str):
    if not os.path.isfile(filePath):
        logger.error("Bill file does not exist: %s", filePath)
        raise Exception("Bill file does not exist: %s", filePath)

    doc_length = 0
    with open(filePath, 'r') as f:
        billText = f.read()
        doc_length = len(billText)
    return doc_length


def getBillLength(billnumber_version: str, pathType=PATHTYPE_DEFAULT) -> int:
    bill_path = billNumberVersionToBillPath(
        billnumber_version=billnumber_version, pathType=pathType)
    return getBillLengthbyPath(bill_path.filePath)


def isDataJson(fileName: str) -> bool:
    return fileName == 'data.json'


def GETBILLPATH_DEFAULT(
    dirName: str,
    fileName: str,
) -> BillPath:
    """
  Returns a BillPath object, with file path, file name, billnumber and version.

  Args:
      dirName (str): The directory name.
      fileName (str): The file name.
  """

    # Add billnumber and billnumber_version to the return value
    billpath = os.path.join(dirName, fileName)
    billnumber_version = CONGRESS_DIRS[PATHTYPE_DEFAULT][
        "pathToBillnumberVersion"](billpath)
    return BillPath(filePath=billpath,
                    fileName=fileName,
                    billnumber_version=billnumber_version)


def walkBillDirs(rootDir=PATH_TO_CONGRESSDATA_DIR,
                 processFile=GETBILLPATH_DEFAULT,
                 dirMatch=PATHTYPE_OBJ["isFileParent"],
                 fileMatch=PATHTYPE_OBJ["fileMatch"]) -> list:
    """
  Walks through the data directory and returns a list of dicts of the form {path: '[path/to]/congress/data/116/...', billnumber_version: '116hr200ih'} with paths to the bill XML files.

  Args:
      rootDir ([type], optional): [description]. Defaults to PATH_TO_CONGRESSDATA_DIR. This is the `congress/data` directory at the location the function is called from.
      processFile ([type], optional): [description]. Defaults to getBillPath.
      dirMatch ([type], optional): [description]. Defaults to isFileParent.
      fileMatch ([type], optional): [description]. Defaults to isDataJson.

  Returns:
      List: A list. Default is List[BillPath], a list of billpaths and (where available) bill numbers and versions. 
  """
    logger.debug("WalkDirs called with the following arguments:")
    logger.debug(locals())
    accumulator = []
    processedNum = 0
    for dirName, _, fileList in os.walk(rootDir):
        if dirMatch(dirName):
            logger.debug('Entering directory: %s' % dirName)
            filteredFileList = [fitem for fitem in fileList if fileMatch(fitem)]
            for fileName in filteredFileList:
                logger.debug('Processing: \t%s' % fileName)
                result = processFile(dirName=dirName, fileName=fileName)
                processedNum += 1
                if processedNum % 100 == 0:
                    logger.debug('Processed %d files' % processedNum)
                if result is not None:
                    accumulator.append(result)
    return accumulator


def getDefaultNamespace(billTree) -> str:
    return billTree.getroot().nsmap.get(None, '')


# Get bill XML paths depending on the pathType
# Uses walkBillDirs with a filter
def getBillXmlPaths(
    congressDataDir: str = PATH_TO_CONGRESSDATA_DIR,
    pathType: str = PATHTYPE_DEFAULT,
    congresses: list[int] = list(
        range(CURRENT_CONGRESS, CURRENT_CONGRESS - 3, -1))
) -> List[BillPath]:
    """
  Returns a list of BillPath objects of the form BillPath(path='data/116/...', billnumber_version='116hr200ih', fileName='Bills-116hr200ih.xml') with paths to the bill XML files for the given congress.
  """
    assert pathType in CONGRESS_DIRS.keys(
    ), "Path type must be in one of the following forms: {}".format(
        str(CONGRESS_DIRS.keys()))
    congressdir_obj = CONGRESS_DIRS[pathType]
    logger.info('Getting bill paths in {}, for congresses: {}'.format(
        congressDataDir, congresses))
    logger.info('pathType: {}'.format(pathType))

    def getBillPath(
        dirName: str,
        fileName: str,
    ) -> BillPath:
        # Add billnumber and billnumber_version to the return value
        billpath = os.path.join(dirName, fileName)
        logger.debug('billpath: {0}'.format(billpath))
        billnumber_version = CONGRESS_DIRS[pathType]["pathToBillnumberVersion"](
            billpath=billpath)
        return BillPath(filePath=billpath,
                        fileName=fileName,
                        billnumber_version=billnumber_version)

    return walkBillDirs(rootDir=congressDataDir,
                        processFile=getBillPath,
                        dirMatch=congressdir_obj["isFileParent"],
                        fileMatch=congressdir_obj["fileMatch"])
