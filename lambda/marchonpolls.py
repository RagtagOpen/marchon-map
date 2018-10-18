import hashlib
import io
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict

import boto3
import requests
from apiclient.discovery import build
from mapbox import Geocoder
from PIL import Image

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def read_sheet(sheet_range, fields, ident_fields, affiliate):
    log.info('\nload sheet %s with %s', os.environ['SHEET_ID'],
             os.environ['GOOGLE_API_KEY'])
    service = build(
        'sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'], cache_discovery=False)
    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ['SHEET_ID'], range=sheet_range).execute()
    values = result.get('values', [])
    rows = {}
    empty = {}
    for field in fields:
        empty[field] = ''
    idx = 0
    for row in values[1:]:
        if not isinstance(ident_fields, list):
            ident_fields = [ident_fields]

        # minus 1 because street_address is optional and another minus 1 because state is optional
        if len(ident_fields) - 2 >= len(row):
            log.warning(
                'Skipping row %s - not enough columns to build identifier', idx)
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

        ident = hashlib.md5()
        for i in ident_fields:
            try:
                ident.update(row[i].encode('utf8'))
            except IndexError:
                pass  # if there isn't a street_address, it's ok
        ident = ident.hexdigest()

        if ident:
            rows[ident] = {
                'id': ident,
                'properties': props
            }
            log.debug('row %s\t%s\t%s',
                      len(rows) + 1, props['name'], ident)
        else:
            log.warning('Skipping "%s" at row %s: no identifier',
                        props['name'], idx)
        idx += 1
    log.info('read %s rows from sheet', len(rows))
    return rows


def get_event_data():
    fields = {
        'name': 1,
        'host': 2,
        'hostContact': 3,
        'hostPhone': 4,
        'eventLink': 5,
        'facebook': 6,
        'twitter': 7,
        'instagram': 8,
        'venue': 9,
        'address': 10,
        'city': 11,
        'state': 12,
        'zip': 13,
        'eventDate': 14,
        'startTime': 15,
        'endTime': 16,
        'description': 17,
        'instructions': 18,
        'email': 19,
        'flagship': 20
    }
    sheet = read_sheet('A1:Z', fields, [1, 10, 11, 12, 14], False)

    # add default name
    for loc in sheet:
        if not sheet[loc]['properties']['name']:
            sheet[loc]['properties']['name'] = '%s Event' % sheet[loc]['properties']['city']

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


def get_geodata(sheet, keys, location_fields, countries=None):
    # in spreadsheet but not GeoJSON
    countries = countries or ['us', 'ca']

    geocoder = Geocoder()
    for key in keys:
        row = sheet[key]
        location = ','.join(
            map(lambda f: row['properties'][f].strip(), location_fields))
        location = row['properties'].get('address') + ", " + location
        resp = geocoder.forward(
            location, limit=1, types=['place', 'address'])
        response = resp.geojson()
        features = response.get('features')

        if not features or location.strip().lower() == 'address':
            if key in sheet:
                del sheet[key]
            log.error('Error geocoding no features %s: %s; %s',
                      key, location, resp.request.url)
            continue

        feature = features[0]
        log.info('geocode %s\n\t%s', location, feature)
        if feature['relevance'] < 0.75:
            log.error('Error geocoding relevance %s: %s', key, location)
            continue
        sheet[key]['geometry'] = feature['geometry']
        # 'place_name': '92646, Huntington Beach, California, United States'
        place_name = feature.get('place_name')
        if place_name:
            place_name = place_name.replace(
                '%s, ' % key, '').replace(', United States', '')
            sheet[key]['properties']['placeName'] = place_name
    # rate limit is 10 per second, this stall keeps us within that
    time.sleep(0.1)


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
        'generated': datetime.now().isoformat(),
        'features': [dataset[key] for key in dataset]
    }
    data['features'] = [x for x in data['features'] if not x.get(
        'properties', {}).get('street_address') == 'Address']
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

    dataset = get_geojson('marchonpolls_events.json')
    log.info('dataset=%s\n', dataset)
    keys = list(set(sheet.keys()) - set(dataset.keys()))
    countries = os.environ.get('COUNTRIES', 'us,ca').split(',')
    if keys:
        get_geodata(
            sheet,
            keys,
            ['city', 'state'],
            countries=countries)
    merge_data(sheet, dataset)
    upload(dataset, 'marchonpolls_events.json', dry_run)
