#!/usr/bin/env python3

from genericpath import isfile
import os, sys
import logging
from typing import Dict, List
import re

from common.constants import CURRENT_CONGRESS, PATH_TO_CONGRESSDATA_DIR, CONGRESS_DIRS
from pymodels import BillPath

logging.basicConfig(filename='utils.log',
                    filemode='w', level='INFO')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

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

  logger.info('In directory: \t%s' % dirName)
  logger.info('Processing: \t%s' % fileName)
  return BillPath(path= os.path.join(dirName, fileName), fileName= fileName)

def isFileParent(dirName: str) -> bool:
  """
  Determines if the directory is the parent of the desired file, e.g. ../../congress/data/116/bills/hr/hr1

  Args:
      dirName (str): path to match 

  Returns:
      [bool]: True if path is a top level (which will contain data.json); False otherwise  
  """
  dirName_parts = dirName.split('/')
  return (re.match(r'[a-z]+[0-9]+', dirName_parts[-1]) is not None and dirName_parts[-3]=='bills')

def isDataJson(fileName: str) -> bool:
  return fileName == 'data.json'

def walkBillDirs(rootDir = PATH_TO_CONGRESSDATA_DIR, processFile = logName, dirMatch = isFileParent, fileMatch = isDataJson):
    for dirName, _, fileList in os.walk(rootDir):
      if dirMatch(dirName):
        logger.info('Entering directory: %s' % dirName)
        filteredFileList = [fitem for fitem in fileList if fileMatch(fitem)]
        for fname in filteredFileList:
            processFile(dirName=dirName, fileName=fname)

# TODO: get bill XML paths depending on the pathType
# Use walkBillDirs with a filter
def getBillXmlPaths(congressDir: str, pathType: str = 'congressdotgov', congresses: list[int] = list(range(CURRENT_CONGRESS, CURRENT_CONGRESS-3, -1))) -> list[str]:
  """
  Returns a list of dicts of the form {path: 'data/116/...', billnumber_version: '116hr200ih'} with paths to the bill XML files for the given congress.
  """
  assert pathType in CONGRESS_DIRS.keys(), "Directory must be in one of the following forms: " + str(CONGRESS_DIRS.keys())

  for congress in congresses:
    congressDir = os.path.join(congressDir, str(congress))
    if not os.path.isdir(congressDir):
      logger.warning('Congress directory %s does not exist.', congressDir)
      continue
    billXmlPaths = []
    for billDir in os.listdir(congressDir):
      billDirPath = os.path.join(congressDir, billDir)
      if os.path.isdir(billDirPath):
        for billXml in os.listdir(billDirPath):
          billXmlPath = os.path.join(billDirPath, billXml)
          if billXml.endswith('.xml'):
            billXmlPaths.append(billXmlPath)
  return billXmlPaths