from datetime import datetime, timedelta
import json
import os

from apiclient.discovery import build
import boto3
from mapbox import Geocoder
import requests

def get_sheet_data():
    try:
        service = build('sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'])
    except:
        # throws errors about file_cache is unavailable when using oauth2client
        # but seems to work fine
        pass
    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ['SHEET_ID'], range='Sheet1!A1:N').execute()
    values = result.get('values', [])
    # 0 Group Name (as shown on website/docs), 1 Location, 2 Form filled out,
    # 3 Main contact name, 4 Title, 5 Main contact info, 6 Secondary contact info
    # 7 Third contact, 8 Org Status, 9 Facebook, 10 Twitter, 11 Insta,
    # 12 Other social link, Website
    # keep these fields
    fields = {'name': 0, 'location': 1, 'contact name': 3, 'contact email': 5,
              'facebook': 9, 'twitter': 10, 'instagram': 11, 'other': 12, 'website': 13}
    location = 1
    rows = {}
    empty = {}
    for field in fields:
        empty[field] = ''
    for row in values[1:]:
        props = {'source': 'sheet'}
        props.update(empty)
        for field in fields:
            idx = fields[field]
            if idx < len(row):
                props[field] = row[idx].strip()
        # skip if no location; nothing to map
        if row[location]:
            rows[row[location]] = {'properties': props}
        else:
            print('WARNING\tskipping %s: no location' % (props['name']))
    print('read %s rows from sheet' % (len(rows)))
    return rows


def get_dataset():
    resp = requests.get('https://s3.amazonaws.com/ragtag-marchon/affiliates.json')
    features = {}
    for feature in resp.json()['features']:
        print('feature=%s' % feature)
        features[feature['properties']['location']] = feature
    print('read %s features' % (len(features)))
    return features


def get_geodata(sheet, keys):
    # in spreadsheet but not GeoJSON
    geocoder = Geocoder()
    for key in keys:
        # San Jose, CA doesn't return results
        response = geocoder.forward(key.replace(', CA', ', California'),
            limit=1, country=['us', 'ca']).geojson()
        if 'features' in response and response['features']:
            feature = response['features'][0]
            print('geocode %s\n\t%s' % (key, feature))
            if feature['relevance'] < 0.9:
                print('WARNING\terror geocoding %s' % (key))
                continue
            sheet[key]['geometry'] = response['features'][0]['geometry']
        else:
            if key in sheet:
                del sheet[key]
            print('WARNING\terror geocoding %s' % (key))


def merge_data(sheet, dataset):
    for key in sheet:
        row = sheet[key]
        if key in dataset and row['properties'] == dataset[key]['properties']:
            print('%s unchanged' % key)
            continue
        print('updating %s' % key)
        if key in dataset:
            dataset[key]['properties'].update(row['properties'])
        else:
            dataset[key] = row
        dataset[key]['type'] = 'Feature'
        if not dataset[key].get('geometry', None):
            del dataset[key]

    orphans = []
    for key in dataset:
        feature = dataset[key]
        if feature.get('source') != 'sheet':
            continue
        if key in sheet:
            continue
        orphans.append(key)
    for key in orphans:
        del dataset[key]

    return dataset


def upload(dataset):
    data = {
        'type': 'FeatureCollection',
        'features': [dataset[key] for key in dataset]
    }
    s3 = boto3.resource('s3')
    print(s3.Object('ragtag-marchon', 'affiliates.json').put(
        Body=json.dumps(data, indent=2),
        ContentType='application/json',
        ACL='public-read',
        Expires=(datetime.now() + timedelta(hours=6))
    ))


def lambda_handler(event=None, context=None):
    sheet = get_sheet_data()
    dataset = get_dataset()
    print('read %s features from dataset' % (len(dataset)))
    keys = sheet.keys() - dataset.keys()
    if keys:
        get_geodata(sheet, keys)
    merge_data(sheet, dataset)
    upload(dataset)
