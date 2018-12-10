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

from action_network import get_events_from_events_campaign, make_key

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
        if len(row) < location_idx:
            log.info('skipping row %s; no location info' % idx)
            continue
        props = {'source': 'events', 'affiliate': affiliate}
        props.update(empty)
        for field in fields:
            idx = fields[field]
            if idx < len(row):
                props[field] = row[idx].strip()
                # Y|N to boolean
                if props[field] == 'Y':
                    props[field] = True
                if props[field] == 'N':
                    props[field] = False
        # skip if no location; nothing to map
        if row[location_idx]:
            rows[row[location_idx].strip()] = {'properties': props}
            log.debug('row %s\t%s\t%s',
                      len(rows) + 1, props['name'], props['location'])
        else:
            log.warning('Skipping "%s" at row %s: no location', props['name'], idx)
        idx += 1
    log.info('read %s rows from sheet', len(rows))
    return rows


def get_event_data():
    '''
    0 January 2018 Anniversary Action Event   1 Event date  2 Event Link  3 Event location
    4 Hosted by:  5 Affiliate?  6 Main contact name   7 Main contact info   8 Facebook
    9 Twitter 10 Insta
    '''
    # keep these fields
    # @RobinColodzin 12.9.2018 - Issue #49 Find out more link missing: field name in json is event Link, not motpLink
    #       Leaving the motpLink as well, adding eventLink
    fields = {'name': 0, 'eventDate': 1, 'eventLink': 2, 'location': 3, 'host': 4,
              'affiliate': 5, 'contactName': 6, 'contactEmail': 7, 'facebook': 8,
              'twitter': 9, 'instagram': 10, 'motpLink': 12, 'eventLink': 12}
    sheet = read_sheet('Sheet1!A1:M', fields, 3, False)

    # add default name
    for loc in sheet:
        if not sheet[loc]['properties']['name']:
            sheet[loc]['properties']['name'] = '%s Event' % loc
    return sheet


def get_sheet_data():
    '''
     0 Group Name (as shown on website/docs), 1 Location, 2 Form filled out,
     3 Main contact name, 4 Title, 5 Main contact info, 6 Secondary contact info
     7 Third contact, 8 Org Status, 9 Facebook, 10 Twitter, 11 Insta,
     12 Other social link, 13 Website, 14 Upcoming event, 15 Event date
     16 Event Link, 17 Photo, 18 About
    '''
    # keep these fields
    fields = {
        'name': 0,
        'location': 1,
        'contactName': 3,
        'contactEmail': 5,
        'facebook': 9,
        'twitter': 10,
        'instagram': 11,
        'other': 12,
        'website': 13,
        'event': 14,
        'eventDate': 15,
        'eventLink': 16,
        'photo': 17,
        'about': 18
    }
    return read_sheet('Sheet1!A1:S', fields, 1, True)


def get_geojson(url):
    log.info('\nload geojson')
    resp = requests.get('https://s3.amazonaws.com/ragtag-marchon/%s' % url)
    features = {}
    for feature in resp.json()['features']:
        # special handling for key for actionnetwork events allows
        # for more than one event per locaion
        # make_key builds a compound key of <location>::<host>
        if feature['properties'].get('source', '') == 'actionnetwork':
            key = make_key(feature['properties'])
        else:
            key = feature['properties']['location']
        features[key] = feature
    log.info('read %s features', len(features))
    return features


def get_location_from_key(key: str) -> str:
    parts = key.split('::', 1)
    return parts[0]


def get_geodata(sheet, keys, countries=None):
    # in spreadsheet but not GeoJSON
    if not countries:
        countries = ['us', 'ca']
    geocoder = Geocoder()
    for key in keys:
        # San Jose, CA doesn't return results
        # special handling for key for actionnetwork events allows
        # for more than one event per locaion
        # make_key builds a compound key of <location>::<host>
        location = get_location_from_key(key).replace(', CA', ', California')
        response = geocoder.forward(location, limit=1, country=countries).geojson()
        if 'features' in response and response['features']:
            feature = response['features'][0]
            log.info('geocode %s\n\t%s', key, feature)
            if feature['relevance'] < 0.75:
                log.warning('Error geocoding %s', key)
                continue
            sheet[key]['geometry'] = feature['geometry']
            # 'place_name': '92646, Huntington Beach, California, United States'
            place_name = feature.get('place_name')
            if place_name:
                place_name = place_name.replace('%s, ' % location, '').\
                    replace(', United States', '')
                sheet[key]['properties']['placeName'] = place_name
        else:
            if key in sheet:
                del sheet[key]
            log.warning('Error geocoding %s', key)


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
        print(data)
    else:
        s3 = boto3.resource('s3')
        response = s3.Object('ragtag-marchon', filename).put(
                Body=json.dumps(data, indent=2),
                ContentType='application/json',
                ACL='public-read',
                Expires=(datetime.now() + timedelta(hours=6)))
        log.info(response)


def resize_photo(service, file):
    log.info('resizing %s', file['name'])
    width = 600
    file_ext = file['mimeType'].split('/')[1]
    filename = '%s.%s' % (file['id'], file_ext.lower())
    data = service.files().get_media(fileId=file['id']).execute()
    img = Image.open(io.BytesIO(data))
    pct = width / float(img.size[0])
    height = int((float(img.size[1]) * float(pct)))
    resized = img.resize((width, height), Image.ANTIALIAS)
    img_bytes = io.BytesIO()
    resized.save(img_bytes, format=file_ext.upper())
    img_bytes.seek(0)
    s3 = boto3.resource('s3')
    response = s3.Object('ragtag-marchon', filename).put(
        Body=img_bytes.read(),
        ContentType=file['mimeType'],
        ACL='public-read',
        Expires=(datetime.now() + timedelta(hours=24 * 7)))
    log.info(response)
    return filename


def update_photos(dataset):
    # map filename to affiliate key
    log.info('\nupdate photos')
    photos = {}
    for key in dataset:
        props = dataset[key]['properties']
        if not props.get('photo', None):
            props['photoUrl'] = ''
            continue
        photos[props['photo']] = key
    try:
        service = build(
            'drive', 'v3', developerKey=os.environ['GOOGLE_API_KEY'])
    except:
        # throws errors about file_cache is unavailable when using oauth2client
        # but seems to work fine
        pass
    query = "'%s' in parents" % os.environ['PHOTO_FOLDER_ID']
    '''
    array of
    {'kind': 'drive#file', 'id': 'abc', 'name': 'photo.jpg', 'mimeType': 'image/jpeg'}
    '''
    file_list = service.files().list(pageSize=1000, q=query).execute()['files']
    for photo in file_list:
        key = photos.get(photo['name'], None)
        if not key:
            log.warning('%s not referenced from dataset', photo['name'])
            continue
        if dataset[key]['properties'].get('photoUrl', None):
            continue
        try:
            url = 'https://s3.amazonaws.com/ragtag-marchon/%s' % resize_photo(
                service, photo)
            log.info('%s saved to %s', photo['name'], url)
            dataset[key]['properties']['photoUrl'] = url
        except:
            log.error('Error resizing photo %s', key)
            traceback.print_exc()


def lambda_handler(event=None, context=None, dry_run=False):
    sheet = get_sheet_data()
    log.info('sheet=%s\n', sheet)
    dataset = get_geojson('affiliates.json')
    sheet.update(get_events_from_events_campaign())
    log.info('dataset=%s\n', dataset)
    keys = sheet.keys() - dataset.keys()
    if keys:
        get_geodata(sheet, keys, os.environ.get('COUNTRIES', 'us,ca').split(','))
    merge_data(sheet, dataset)
    update_photos(dataset)
    upload(dataset, 'affiliates.json', dry_run)


def events_lambda_handler(event=None, context=None, dry_run=False):
    sheet = get_event_data()
    log.info('sheet=%s\n', sheet)

    log.info('\nstart get Action Network events')
    action_network_events = get_events_from_events_campaign()
    log.info('\ngot %d events from action network', len(action_network_events))
    log.info('action_network_events=%s\n', action_network_events)

    sheet.update(action_network_events)

    dataset = get_geojson('events.json')
    log.info('dataset=%s\n', dataset)
    keys = sheet.keys() - dataset.keys()
    countries = os.environ.get('COUNTRIES', 'us,ca').split(',')
    if keys:
        get_geodata(
            sheet,
            keys,
            countries=countries)
    merge_data(sheet, dataset)
    upload(dataset, 'events.json', dry_run)
