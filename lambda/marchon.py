import json
import os

from apiclient.discovery import build
from mapbox import Datasets, Geocoder

def get_sheet_data():
    service = build('sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'])
    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ['SHEET_ID'], range='Sheet1!A1:N').execute()
    values = result.get('values', [])
    # ['Group Name (as shown on website/docs)', 'Location', 'Form filled out', 'Main contact name', 'Title', 'Main contact info', 'Secondary contact info', 'Third contact', 'Facebook', 'Twitter', 'Insta', 'Other social link', 'Kit sent? ', 'Website']
    # keep these fields
    fields = {'name': 0, 'contact name': 3, 'contact email': 5, 'facebook': 8,
              'twitter': 9, 'instagram': 10, 'other': 11, 'website': 13}
    location = 1
    rows = {}
    empty = {}
    for field in fields:
        empty[field] = ''
    for row in values[1:]:
        props = {}
        props.update(empty)
        for field in fields:
            idx = fields[field]
            if idx < len(row):
                props[field] = row[idx]
        rows[row[location]] = {'properties': props}
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
        response = geocoder.forward(key, limit=1)
        print('geocode %s\t%s' % (key, response.geojson()['features'][0]))
        sheet[key]['geometry'] = response.geojson()['features'][0]['geometry']


def merge_data(sheet, dataset):
    datasets = Datasets(access_token=os.environ['MAPBOX_ACCESS_TOKEN'])
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
        print(datasets.update_feature(os.environ['DATASET_ID'], key, dataset[key]).json())


def lambda_handler(event=None, context=None):
    sheet = get_sheet_data()
    print('read %s rows from sheet' % (len(sheet)))
    dataset = get_dataset()
    print('read %s features from dataset' % (len(dataset)))
    new_rows = sheet.keys() - dataset.keys()
    if new_rows:
        get_geodata(sheet, new_rows)
    merge_data(sheet, dataset)
