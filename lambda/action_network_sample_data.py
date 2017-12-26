def make_test_email():
    return {
        'address': 'LP10011@gmail.com',
        'primary': True,
        'status': 'subscribed'
    }


def make_test_location():
    return {
        'address_lines': ['2753 Broadway'],
        'country': 'US',
        'locality': 'New York',
        'location': {
            'accuracy': 'Rooftop',
            'latitude': 40.801169242022034,
            'longitude': -73.96804986401399
        },
        'postal_code': '10025',
        'region': 'NY',
        'venue': 'Larry\'s house'
    }


def make_test_organizer():
    return {
        '_links': {
            'osdi:attendances': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/attendances'
            },
            'osdi:donations': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/donations'
            },
            'osdi:outreaches': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/outreaches'
            },
            'osdi:signatures': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/signatures'
            },
            'osdi:submissions': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/submissions'
            },
            'osdi:taggings': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/taggings'
            },
            'self': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051'
            }
        },
        'created_date':
        '2016-11-16T14:09:15Z',
        'custom_fields': {},
        'email_addresses': [make_test_email()],
        'family_name':
        'Person',
        'given_name':
        'Larry',
        'identifiers': ['action_network:38cc1710-4a71-4225-9607-e8269758e051'],
        'languages_spoken': ['en'],
        'modified_date':
        '2017-12-22T18:55:05Z',
        'postal_addresses': [{
            'country': 'US',
            'locality': 'New York',
            'location': {
                'accuracy': 'Approximate',
                'latitude': 40.798,
                'longitude': -73.9674
            },
            'postal_code': '10025',
            'primary': True,
            'region': 'NY'
        }]
    }


def make_test_event():
    return {
        '_embedded': {
            'osdi:creator': {
                '_links': {
                    'osdi:attendances': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/attendances'
                    },
                    'osdi:donations': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/donations'
                    },
                    'osdi:outreaches': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/outreaches'
                    },
                    'osdi:signatures': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/signatures'
                    },
                    'osdi:submissions': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/submissions'
                    },
                    'osdi:taggings': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051/taggings'
                    },
                    'self': {
                        'href':
                        'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051'
                    }
                },
                'created_date':
                '2016-11-16T14:09:15Z',
                'custom_fields': {},
                'email_addresses': [{
                    'address': 'LP10011@gmail.com',
                    'primary': True,
                    'status': 'subscribed'
                }],
                'family_name':
                'Person',
                'given_name':
                'Larry',
                'identifiers':
                ['action_network:38cc1710-4a71-4225-9607-e8269758e051'],
                'languages_spoken': ['en'],
                'modified_date':
                '2017-12-22T18:55:05Z',
                'postal_addresses': [{
                    'country': 'US',
                    'locality': 'New '
                    'York',
                    'location': {
                        'accuracy': 'Approximate',
                        'latitude': 40.798,
                        'longitude': -73.9674
                    },
                    'postal_code': '10025',
                    'primary': True,
                    'region': 'NY'
                }]
            },
            'osdi:organizer': make_test_organizer(),
        },
        '_links': {
            'action_network:embed': {
                'href':
                'https://actionnetwork.org/api/v2/events/5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d/embed'
            },
            'action_network:event_campaign': {
                'href':
                'https://actionnetwork.org/api/v2/event_campaigns/9e5b2755-9161-446e-93a4-78ac0ef6a206'
            },
            'osdi:attendances': {
                'href':
                'https://actionnetwork.org/api/v2/events/5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d/attendances'
            },
            'osdi:creator': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051'
            },
            'osdi:organizer': {
                'href':
                'https://actionnetwork.org/api/v2/people/38cc1710-4a71-4225-9607-e8269758e051'
            },
            'osdi:record_attendance_helper': {
                'href':
                'https://actionnetwork.org/api/v2/events/5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d/attendances'
            },
            'record_attendance_helper': {
                'href':
                'https://actionnetwork.org/api/v2/events/5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d/attendances'
            },
            'self': {
                'href':
                'https://actionnetwork.org/api/v2/events/5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d'
            }
        },
        'action_network:event_campaign_id':
        '9e5b2755-9161-446e-93a4-78ac0ef6a206',
        'action_network:hidden':
        False,
        'browser_url':
        'https://actionnetwork.org/events/after-party',
        'created_date':
        '2017-12-22T21:38:51Z',
        'description':
        '<p>Test House Party Event</p>',
        'guests_can_invite_others':
        True,
        'identifiers': ['action_network:5450dbe7-99c7-4b8e-a7a3-9b2db76cc41d'],
        'instructions':
        '<p>Thanks for joining our '
        'event</p>',
        'location':
        make_test_location(),
        'modified_date':
        '2017-12-22T21:47:19Z',
        'name':
        'Larry\'s party',
        'origin_system':
        'Action Network',
        'reminders': [{
            'method': 'email',
            'minutes': 1440
        }],
        'start_date':
        '2018-01-20T18:00:00Z',
        'status':
        'confirmed',
        'title':
        'After party',
        'total_accepted':
        1,
        'transparence':
        'opaque',
        'visibility':
        'public'
    }
