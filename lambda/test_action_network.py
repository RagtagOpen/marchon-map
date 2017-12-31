import pprint

from action_network import (convert_event, get_email_address_from_organizer,
                            get_events_from_events_campaign, get_organizer,
                            make_location)
from action_network_sample_data import make_test_event, make_test_location
from common import LocationHostKey


def test_make_location_everything():
    location = make_location({'location': make_test_location()})
    assert location == '10025'


def test_make_location_nothing():
    inner_loc = make_test_location()
    del inner_loc['locality']
    del inner_loc['region']
    del inner_loc['postal_code']
    location = make_location({'location': inner_loc})
    assert location == ''


def test_make_location_none():
    location = make_location({'location': None})
    assert location == ''


def test_make_location_not_us():
    inner_loc = make_test_location()
    inner_loc['country'] = 'New Zealand'
    location = make_location({'location': inner_loc})
    assert location == 'New York, New Zealand'


def test_get_organizer():
    x = get_organizer({
        '_embedded': {
            'osdi:organizer': {
                'given_name': 'larry'
            }
        }
    })
    assert x == {'given_name': 'larry'}


def test_get_organizer_no_organizer():
    x = get_organizer({
        '_embedded': {
            'osdi:organizer_xx': {
                'given_name': 'larry'
            }
        }
    })
    assert x == {}


def test_get_organizer_none_organizer():
    x = get_organizer({'_embedded': {'osdi:organizer': None}})
    assert x == {}


def test_get_organizer_no_embedded():
    x = get_organizer({'_embedded_xx': {'osdi:organizer': None}})
    assert x == {}


def test_get_organizer_none_embedded():
    x = get_organizer({'_embeddedx': None})
    assert x == {}


def test_get_email_address():
    x = get_email_address_from_organizer({
        'email_addresses': [{
            'address': 'foo@gmail.com',
            'primary': True
        }, {
            'address': 'ignore',
            'primary': False
        }]
    })
    assert x == 'foo@gmail.com'
    x = get_email_address_from_organizer({
        'email_addresses': [{
            'address': 'ignore',
            'primary': False
        }, {
            'address': 'foo@gmail.com',
            'primary': True
        }]
    })
    assert x == 'foo@gmail.com'
    x = get_email_address_from_organizer({
        'email_addresses': [{
            'address': 'ignore',
            'primary': False
        }, {
            'address': 'foo@gmail.com',
            'primary': False
        }]
    })
    assert x == 'ignore'


def test_convert_event():
    x = convert_event(make_test_event())
    lhk = LocationHostKey('10025', 'Larry Person')
    assert lhk in x
    converted_event = x[lhk]
    assert 'properties' in converted_event
    p = converted_event['properties']
    assert p['source'] == 'actionnetwork'
    assert not p['affiliate']
    assert p['name'] == 'Larry\'s party'
    assert p['eventDate'] == '1/20/2018'
    assert p['eventLink'] == 'https://actionnetwork.org/events/after-party'
    assert p['location'] == '10025'
    assert p['contactEmail'] == 'LP10011@gmail.com'
    assert p['host'] == 'Larry Person'
    assert p['contactName'] == 'Larry Person'


if __name__ == '__main__':
    the_events = get_events_from_events_campaign()
    pp = pprint.PrettyPrinter()
    pp.pprint(the_events)
