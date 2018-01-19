import logging
import os
from typing import Dict

import requests
from dateutil import parser

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def make_location(event: Dict) -> str:
    location = (event.get('location', {}) or {})
    if location.get('country', 'US') != 'US':
        return '{city}, {country}'.format(
            city=location.get('locality'), country=location.get('country'))
    return location.get('postal_code', '')


def get_organizer(event: Dict) -> Dict:
    embedded = event.get('_embedded') or {}
    return embedded.get('osdi:organizer') or {}


def get_contact_name(event: Dict) -> Dict:
    organizer = get_organizer(event)
    given_name = organizer.get('given_name')
    family_name = organizer.get('family_name')

    name = ''
    if given_name:
        name = given_name
    if given_name and family_name:
        name += ' '
    if family_name:
        name += family_name
    return name


def get_email_address_from_organizer(organizer: Dict) -> str:
    email_addresses = organizer.get('email_addresses', {})
    next_best_email_address = ''
    for this_email_address in email_addresses:
        address = this_email_address.get('address')
        if this_email_address.get('primary'):
            return address
        elif not next_best_email_address:
            next_best_email_address = address

    return next_best_email_address


def get_email_address(event: Dict) -> str:
    return get_email_address_from_organizer(get_organizer(event))


def get_events_from_events_campaign(return_events=None,
                                    page=1) -> Dict[str, Dict]:
    if not return_events:
        return_events = {}

    log.info('\nget_events_from events_campaign (action network) -- page %d',
             page)

    response = requests.get(
        'https://actionnetwork.org/api/v2/event_campaigns/{event_campaign_id}/events?page={page}'.
        format(
            event_campaign_id=os.environ['ACTION_NETWORK_EVENTS_CAMPAIGN_ID'],
            page=page),
        headers={
            'OSDI-API-Token': os.environ['ACTION_NETWORK_API_KEY']
        })
    if response.status_code != 200:
        log.error(
            'ERROR\tResponse code %d received from https://actionnetwork.org/api/v2/event_campaigns',
            response.status_code)
        return {}

    log.info(
        '\nsuccess! get_events_from events_campaign (action network) -- page %d',
        page)

    response_json = response.json()
    events = response_json.get('_embedded', {}).get('osdi:events', {})
    for event in events:
        return_events.update(convert_event(event))

    if response_json.get('total_pages', page) > page:
        get_events_from_events_campaign(return_events, page + 1)

    return return_events


def make_key(properties: Dict) -> str:
    return '{location}::{host}'.format(
        location=properties.get('location', ''),
        host=properties.get('host', ''))


def convert_event(event: Dict) -> Dict:
    contact_name = get_contact_name(event)
    #yapf:disable
    properties = {
        'source': 'actionnetwork',
        'affiliate': False,
        'name': event.get('name') or event.get('title') or '',
        'eventDate': parser.parse(event.get(
            'start_date', '1/20/2018')).strftime('%-m/%-d/%Y'),
        'eventLink': event.get('browser_url', ''),
        'motpLink': event.get('browser_url', ''),
        'location': make_location(event),
        'contactEmail': get_email_address_from_organizer(get_organizer(event)),
        'host': contact_name,
        'contactName': contact_name,
        'facebook': '',
        'instagram': '',
        'twitter': '',
    }
    #yapf:enable
    return {
        # special handling for key for actionnetwork events allows
        # for more than one event per locaion
        # make_key builds a compound key of <location>::<host>
        make_key(properties): {
            'properties': properties,
        }
    }
