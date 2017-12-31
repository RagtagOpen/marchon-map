from typing import Dict


def make_key(properties: Dict) -> str:
    return '{location}::{host}'.format(
        location=properties.get('location', ''),
        host=properties.get('host', ''))
