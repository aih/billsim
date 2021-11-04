#!/usr/bin/env python3

import os
import logging
from typing import Dict, List

from common.constants import CURRENT_CONGRESS

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

def get_bill_xml_paths(congressDir: str, pathType: str = 'congressdotgov', congresses: list[int] = list(range(CURRENT_CONGRESS, CURRENT_CONGRESS-3, -1))) -> list[str]:
  """
  Returns a list of dicts of the form {path: 'data/116/...', billnumber_version: '116hr200ih'} with paths to the bill XML files for the given congress.
  """
  assert pathType in ['congressdotgov', 'unitedstates', 'lrc']

  for congress in congresses:
    congressDir = os.path.join(congressDir, str(congress))
    if not os.path.isdir(congressDir):
      logger.warning('Congress directory %s does not exist.', congressDir)
      continue
    billXmlPaths = []
    # TODO: get bill XML paths depending on the pathType
    # Use walkdir with a filter
    for billDir in os.listdir(congressDir):
      billDirPath = os.path.join(congressDir, billDir)
      if os.path.isdir(billDirPath):
        for billXml in os.listdir(billDirPath):
          billXmlPath = os.path.join(billDirPath, billXml)
          if billXml.endswith('.xml'):
            billXmlPaths.append(billXmlPath)
  return billXmlPaths