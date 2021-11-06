#!/usr/bin/env python3

from genericpath import isfile
import os, sys
import logging
from typing import Dict, List

from common.constants import CURRENT_CONGRESS, PATH_TO_CONGRESSDATA_DIR, CONGRESS_DIRS
from common.pymodels import BillPath

logging.basicConfig(filename='utils.log',
                    filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

CDG = CONGRESS_DIRS["congressdotgov"]

def getText(item) -> str:
  if item is None:
    return ''

  try:
    if isinstance(item, list):
        item = item[0]
    return item.text
  except:
    return ''

def logName(dirName: str, fileName: str) -> BillPath:
  """
  Prints the name provided (path to a file to be processed) to the log.
  Returns the file path and file name.

  Args:
      fname (str): path of file to be processed 
  """

  logger.debug('In directory: \t%s' % dirName)
  logger.debug('Processing: \t%s' % fileName)
  return BillPath(path= os.path.join(dirName, fileName), fileName= fileName)

def isDataJson(fileName: str) -> bool:
  return fileName == 'data.json'

def walkBillDirs(rootDir = PATH_TO_CONGRESSDATA_DIR, processFile = logName, dirMatch = CDG["isFileParent"], fileMatch = CDG["fileMatch"]) -> list:
  """
  Walks through the data directory and returns a list of dicts of the form {path: '[path/to]/congress/data/116/...', billnumber_version: '116hr200ih'} with paths to the bill XML files.

  Args:
      rootDir ([type], optional): [description]. Defaults to PATH_TO_CONGRESSDATA_DIR. This is the `congress/data` directory at the location the function is called from.
      processFile ([type], optional): [description]. Defaults to logName.
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
      for fname in filteredFileList:
          result = processFile(dirName=dirName, fileName=fname)
          processedNum += 1
          if processedNum % 100 == 0:
            logger.info('Processed %d files' % processedNum)
          if result is not None:
              accumulator.append(result)
  return accumulator

# Get bill XML paths depending on the pathType
# Uses walkBillDirs with a filter
def getBillXmlPaths(congressDir: str=PATH_TO_CONGRESSDATA_DIR, pathType: str = 'congressdotgov', congresses: list[int] = list(range(CURRENT_CONGRESS, CURRENT_CONGRESS-3, -1))) -> List[BillPath]:
  """
  Returns a list of dicts of the form {path: 'data/116/...', billnumber_version: '116hr200ih'} with paths to the bill XML files for the given congress.
  """
  assert pathType in CONGRESS_DIRS.keys(), "Directory must be in one of the following forms: " + str(CONGRESS_DIRS.keys())
  congressdir = CONGRESS_DIRS[pathType]
  return walkBillDirs(rootDir = congressDir, processFile=logName, dirMatch = congressdir["isFileParent"], fileMatch = congressdir["fileMatch"])