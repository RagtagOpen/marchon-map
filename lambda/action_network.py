import logging
import os
from typing import Dict

import requests
from dateutil import parser

log = logging.getLogger(__name__)


def get_object_or_empty_dict(key: str, event: Dict) -> Dict:
    location = event.get(key)
    if not location:
        location = {}
    return location


def make_location(event: Dict) -> str:
    location = get_object_or_empty_dict('location', event)
    if location.get('country', 'US') != 'US':
        return '{city}, {country}'.format(
            city=location.get('locality'), country=location.get('country'))
    return location.get('postal_code', '')


def get_event_name(event: Dict) -> str:
    name = event.get('name', None)
    if not name:
        name = event.get('title', '')
    return name


def get_organizer(event: Dict) -> Dict:
    return get_object_or_empty_dict('osdi:organizer',
                                    get_object_or_empty_dict(
                                        '_embedded', event))


def get_contact_name(event: Dict) -> Dict:
    organizer = get_organizer(event)
    given_name = organizer.get('given_name')
    family_name = organizer.get('family_name')
    return ' '.join([given_name, family_name])


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
                                    page=None) -> Dict[str, Dict]:
    if not return_events:
        return_events = {}
    if not page:
        page = 1

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

    response_json = response.json()
    events = response_json.get('_embedded', {}).get('osdi:events', {})
    for event in events:
        converted_event = convert_event(event)
        return_events[make_key(converted_event)] = converted_event

    if response_json.get('total_pages', page) > page:
        get_events_from_events_campaign(return_events, page + 1)

    return return_events


def make_key(converted_event: Dict) -> str:
    return '{location}::{host}'.format(
        location=converted_event['properties']['location'],
        host=converted_event['properties']['host'])


def convert_event(event: Dict) -> Dict:
    properties = {
        'source':
        'actionnetwork',
        'affiliate':
        False,
        'name':
        get_event_name(event),
        'eventDate':
        parser.parse(event.get('start_date',
                               '1/20/2018')).strftime('%-m/%-d/%Y'),
        'eventLink':
        event.get('browser_url', ''),
        'location':
        make_location(event),
        'contactEmail':
        get_email_address(event),
        'host':
        get_contact_name(event),
        'contactName':
        get_contact_name(event),
        'facebook':
        '',
        'instagram':
        '',
        'twitter':
        '',
    }
    return {
        'properties': properties,
    }
