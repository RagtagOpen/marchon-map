import json
import os

from apiclient.discovery import build
from mapbox import Datasets, Geocoder

def get_sheet_data():
    service = build('sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'])
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
    return rows


def get_dataset():
    datasets = Datasets(access_token=os.environ['MAPBOX_ACCESS_TOKEN'])
    features = {}
    for feature in datasets.list_features(os.environ['DATASET_ID']).json()['features']:
        features[feature['id']] = feature
    return features


def get_geodata(sheet, keys):
    # in spreadsheet but not GeoJSON
    geocoder = Geocoder()
    for key in keys:
        response = geocoder.forward(key, limit=1).geojson()
        if 'features' in response and response['features']:
            feature = response['features'][0]
            print('geocode %s\n\t%s' % (key, feature))
            if feature['relevance'] < 0.9:
                print('WARNING\terror geocoding %s' % (key))
                continue
            sheet[key]['geometry'] = response['features'][0]['geometry']
        else:
            print('WARNING\terror geocoding %s' % (key))


def merge_data(sheet, dataset):
    datasets = Datasets(access_token=os.environ['MAPBOX_ACCESS_TOKEN'])
    ds_id = os.environ['DATASET_ID']
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
        print('\t%s' % datasets.update_feature(ds_id, key, dataset[key]).json())


def delete_orphans(sheet, dataset):
    datasets = Datasets(access_token=os.environ['MAPBOX_ACCESS_TOKEN'])
    ds_id = os.environ['DATASET_ID']
    for key in dataset:
        feature = dataset[key]
        if feature.get('source') != 'sheet':
            continue
        # if in dataset but not sheet
        if key not in sheet:
            print('deleting %s: in dataset but not sheet')
        print('\t%s' % datasets.delete_feature(ds_id, key).json())


def lambda_handler(event=None, context=None):
    sheet = get_sheet_data()
    print('read %s rows from sheet' % (len(sheet)))
    dataset = get_dataset()
    print('read %s features from dataset' % (len(dataset)))
    keys = sheet.keys() - dataset.keys()
    if keys:
        get_geodata(sheet, keys)
    merge_data(sheet, dataset)
    delete_orphans(sheet, dataset)
