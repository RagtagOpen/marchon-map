import json

import requests_mock

import marchon
'''
    set these in environment

    GOOGLE_API_KEY
    SHEET_ID
    MAPBOX_ACCESS_TOKEN
'''




def test_get_geojson():
    def response_callback(_, context):
        features = {
            "type":
            "FeatureCollection",
            "features": [{
                "properties": {
                    "source": "events",
                    "location": "New Paltz, NY",
                    "host": "March On Hudson Valley",
                },
                "type": "Feature"
            }, {
                'properties': {
                    'source': 'actionnetwork',
                    'host': 'Mark Langgin',
                    'location': 'Des '
                    'Moines, IA '
                    '50312',
                }
            }]
        }
        context.status_code = 200
        return json.dumps(features)

    with requests_mock.Mocker() as mock:
        mock.get(
            'https://s3.amazonaws.com/ragtag-marchon/events.json',
            text=response_callback)
        x = marchon.get_geojson('events.json')
        assert len(x) == 2
        assert 'New Paltz, NY' in x
        assert 'Des Moines, IA 50312::Mark Langgin' in x


def test_get_location_from_key():
    x = marchon.get_location_from_key('New York, NY 10025::Larry Person')
    assert x == 'New York, NY 10025'
    x = marchon.get_location_from_key('New York, NY 10025:Larry Person')
    assert x == 'New York, NY 10025:Larry Person'
    x = marchon.get_location_from_key('New York, NY 10025')
    assert x == 'New York, NY 10025'


if __name__ == '__main__':
    # print output instead of saving to S3
    marchon.events_lambda_handler(event=None, context=None, dry_run=True)
