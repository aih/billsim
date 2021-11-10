#!/usr/bin/env python3

from functools import reduce
import os, sys
import logging
from typing import Dict, List

from billsim.constants import CURRENT_CONGRESS, PATH_TO_CONGRESSDATA_DIR, CONGRESS_DIRS
from billsim.pymodels import BillPath

logging.basicConfig(filename='utils.log', filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

CDG = CONGRESS_DIRS["congressdotgov"]

def deep_get(dictionary: Dict, *keys):
  """
  A Dict utility to get a field; returns None if the field does not exist

  Args:
      dictionary (Dict): an arbitrary dictionary 

  Returns:
      any: value of the specified key, or None if the field does not exist
  """
  return reduce(
    lambda d, key: d.get(key, None) if isinstance(d, dict) else None, keys, 
    dictionary)

def getText(item) -> str:
    if item is None:
        return ''

    try:
        if isinstance(item, list):
            item = item[0]
        return item.text
    except:
        return ''


def getBillPath(dirName: str,
                fileName: str,
                pathType: str = 'congressdotgov') -> BillPath:
    """
  Returns a BillPath object, with file path, file name, billnumber and version.

  Args:
      dirName (str): The directory name.
      fileName (str): The file name.
  """

    assert pathType in CONGRESS_DIRS.keys(
    ), "Path type must be in one of the following forms: " + str(
        CONGRESS_DIRS.keys())
    # Add billnumber and billnumber_version to the return value
    billpath = os.path.join(dirName, fileName)
    billnumber_version = CONGRESS_DIRS[pathType]["pathToBillnumberVersion"](
        billpath)
    return BillPath(path=billpath,
                    fileName=fileName,
                    billnumber_version=billnumber_version)


def isDataJson(fileName: str) -> bool:
    return fileName == 'data.json'


def walkBillDirs(rootDir=PATH_TO_CONGRESSDATA_DIR,
                 processFile=getBillPath,
                 dirMatch=CDG["isFileParent"],
                 fileMatch=CDG["fileMatch"]) -> list:
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
            filteredFileList = [
                fitem for fitem in fileList if fileMatch(fitem)
            ]
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
    congressDir: str = PATH_TO_CONGRESSDATA_DIR,
    pathType: str = 'congressdotgov',
    congresses: list[int] = list(
        range(CURRENT_CONGRESS, CURRENT_CONGRESS - 3, -1))
) -> List[BillPath]:
    """
  Returns a list of BillPath objects of the form BillPath(path='data/116/...', billnumber_version='116hr200ih', fileName='Bills-116hr200ih.xml') with paths to the bill XML files for the given congress.
  """
    assert pathType in CONGRESS_DIRS.keys(
    ), "Path type must be in one of the following forms: " + str(
        CONGRESS_DIRS.keys())
    congressdir = CONGRESS_DIRS[pathType]
    return walkBillDirs(rootDir=congressDir,
                        processFile=getBillPath,
                        dirMatch=congressdir["isFileParent"],
                        fileMatch=congressdir["fileMatch"])