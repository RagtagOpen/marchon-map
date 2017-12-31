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
        #yapf:disable
        features = {
            'type':
            'FeatureCollection',
            'features': [{
                'properties': {
                    'source': 'events',
                    'location': 'New Paltz, NY',
                    'host': 'March On Hudson Valley',
                },
                'type': 'Feature'
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
        #yapf:enable
        context.status_code = 200
        return json.dumps(features)

    with requests_mock.Mocker() as mock:
        mock.get(
            'https://s3.amazonaws.com/ragtag-marchon/events.json',
            text=response_callback)
        x = marchon.get_geojson('events.json')
        assert len(x) == 2
        assert 'New Paltz, NY::March On Hudson Valley' in x
        assert 'Des Moines, IA 50312::Mark Langgin' in x


if __name__ == '__main__':
    # print output instead of saving to S3
    marchon.events_lambda_handler(event=None, context=None, dry_run=True)
