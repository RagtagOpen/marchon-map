from typing import Dict
from collections import namedtuple

LocationHostKey = namedtuple('LocationHostKey', ['location', 'host'])


def make_key(properties: Dict) -> LocationHostKey:
    return LocationHostKey(
        properties.get('location') or '',
        properties.get('host', '')
    )
