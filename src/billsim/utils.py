#!/usr/bin/env python3

from functools import reduce
import os, sys
import re
import logging
from typing import List

from billsim.constants import PATHTYPE_DEFAULT, PATHTYPE_OBJ, CURRENT_CONGRESS, PATH_TO_CONGRESSDATA_DIR, CONGRESS_DIRS
from billsim.pymodels import BillPath

import traceback

logging.basicConfig(filename='utils.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
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


def getEnum(section, defaultNS=None) -> str:
    if defaultNS is not None:
        enumpath = section.xpath('ns:enum', namespaces={'ns': defaultNS})
    else:
        enumpath = section.xpath('enum')
    if len(enumpath) > 0:
        return enumpath[0].text
    return ''


def getHeader(section, defaultNS=None) -> str:
    if defaultNS is not None:
        headerpath = section.xpath('header', namespaces={'ns': defaultNS})
    else:
        headerpath = section.xpath('header')
    if len(headerpath) > 0:
        return headerpath[0].text
    return ''


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
