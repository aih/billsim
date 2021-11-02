#!/usr/bin/env python3

import logging

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