from datetime import datetime, timedelta
import io
import json
import logging
import os
import traceback
from typing import Dict

import boto3
import requests
from apiclient.discovery import build
from mapbox import Geocoder
from PIL import Image

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def read_sheet(sheet_range, fields, location_idx, affiliate):
    log.info('\nload sheet %s with %s', os.environ['SHEET_ID'],
             os.environ['GOOGLE_API_KEY'])
    service = build('sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'], cache_discovery=False)
    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ['SHEET_ID'], range=sheet_range).execute()
    values = result.get('values', [])
    rows = {}
    empty = {}
    for field in fields:
        empty[field] = ''
    idx = 0
    for row in values[1:]:
        if not isinstance(location_idx, list):
            location_idx = [location_idx]

        if max(location_idx) >= len(row):
            log.warning('Skipping row %d because no location', idx)
            continue

        props = {}
        props.update(empty)
        for field in fields:
            idx = fields[field]
            if idx < len(row):
                val = row[idx].strip()
                if val:
                    props[field] = val

                # Y|N to boolean
                if props[field] == 'Y':
                    props[field] = True
                if props[field] == 'N':
                    props[field] = False
        location = ' '.join(map(lambda f: row[f].strip(), location_idx))
        if location:
            rows[location] = {
                'id': location,
                'properties': props
            }
            log.debug('row %s\t%s\t%s',
                      len(rows) + 1, props['name'], rows[location]['id'])
        else:
            log.warning('Skipping "%s" at row %s: no location', props['name'], idx)
        idx += 1
    log.info('read %s rows from sheet', len(rows))
    return rows


def get_event_data():
    fields = {
        'name': 0,
        'eventDate': 1,
        'eventLink': 2,
        'city': 3,
        'state': 4,
        'country': 5,
        'host': 6,
        'affiliate': 7,
        'contactName': 8,
        'contactEmail': 9,
        'facebook': 10,
        'twitter': 11,
        'instagram': 12,
    }
    sheet = read_sheet('Sheet1!A1:M', fields, [3, 4, 5], False)

    # add default name
    for loc in sheet:
        if not sheet[loc]['properties']['name']:
            sheet[loc]['properties']['name'] = '%s Event' % loc
    return sheet


def get_geojson(url):
    log.info('\nload geojson')
    resp = requests.get('https://s3.amazonaws.com/ragtag-marchon/%s' % url)
    features = {}

    if resp.status_code != 200:
        # It hasn't been created yet
        log.info('no existing geojson found')
        return features

    for feature in resp.json()['features']:
        key = feature.get('id')
        features[key] = feature

    log.info('read %s features', len(features))
    return features


def get_geodata(sheet, keys, countries=None):
    # in spreadsheet but not GeoJSON
    if not countries:
        countries = ['us', 'ca']
    geocoder = Geocoder()
    for key in keys:
        response = geocoder.forward(key, limit=1, types=['place']).geojson()
        features = response.get('features')

        if not features:
            if key in sheet:
                del sheet[key]
            log.warning('Error geocoding %s', key)
            continue

        feature = features[0]
        log.info('geocode %s\n\t%s', key, feature)
        if feature['relevance'] < 0.75:
            log.warning('Error geocoding %s', key)
            continue
        sheet[key]['geometry'] = feature['geometry']
        # 'place_name': '92646, Huntington Beach, California, United States'
        place_name = feature.get('place_name')
        if place_name:
            place_name = place_name.replace('%s, ' % key, '').replace(', United States', '')
            sheet[key]['properties']['placeName'] = place_name


def merge_data(sheet, dataset):
    for key in sheet:
        row = sheet[key]
        if key in dataset and row['properties'] == dataset[key]['properties']:
            log.info('%s unchanged', key)
            continue
        log.info('updating %s', key)
        if key in dataset:
            dataset[key]['properties'].update(row['properties'])
        else:
            dataset[key] = row
        dataset[key]['type'] = 'Feature'
        if not dataset[key].get('geometry', None):
            log.info('%s missing geometry; deleting', key)
            del dataset[key]

    orphans = []
    for key in dataset:
        if key in sheet:
            log.info('%s in dataset and sheet', key)
            continue
        orphans.append(key)
    log.info('%s orphans: %s', len(orphans), orphans)
    for key in orphans:
        del dataset[key]

    return dataset


def upload(dataset, filename, dry_run):
    data = {
        'type': 'FeatureCollection',
        'features': [dataset[key] for key in dataset]
    }
    if dry_run:
        print(json.dumps(data))
    else:
        s3 = boto3.resource('s3')
        response = s3.Object('ragtag-marchon', filename).put(
                Body=json.dumps(data, indent=2),
                ContentType='application/json',
                ACL='public-read',
                Expires=(datetime.now() + timedelta(hours=6)))
        log.info(response)


def events_lambda_handler(event=None, context=None, dry_run=False):
    sheet = get_event_data()
    log.info('sheet=%s\n', sheet)

    dataset = get_geojson('family_separation_events.json')
    log.info('dataset=%s\n', dataset)
    keys = sheet.keys() - dataset.keys()
    countries = os.environ.get('COUNTRIES', 'us,ca').split(',')
    if keys:
        get_geodata(
            sheet,
            keys,
            countries=countries)
    merge_data(sheet, dataset)
    upload(dataset, 'family_separation_events.json', dry_run)
