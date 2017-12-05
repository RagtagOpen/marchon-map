from datetime import datetime, timedelta
import io
import json
import os
import traceback

from apiclient.discovery import build
import boto3
from mapbox import Geocoder
from PIL import Image
import requests

def read_sheet(sheet_range, fields, location_idx, affiliate):
    print('\nload sheet %s with %s' % (os.environ['SHEET_ID'], os.environ['GOOGLE_API_KEY']));
    try:
        service = build('sheets', 'v4', developerKey=os.environ['GOOGLE_API_KEY'])
    except:
        # throws errors about file_cache is unavailable when using oauth2client
        # but seems to work fine
        pass
    result = service.spreadsheets().values().get(
        spreadsheetId=os.environ['SHEET_ID'], range=sheet_range).execute()
    values = result.get('values', [])
    rows = {}
    empty = {}
    for field in fields:
        empty[field] = ''
    for row in values[1:]:
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
            print('row %s\t%s\t%s' % (len(rows) + 1, props['name'], props['location']))
        else:
            print('WARNING\tskipping %s: no location' % (props['name']))
    print('read %s rows from sheet' % (len(rows)))
    return rows


def get_event_data():
    '''
    0 January 2018 Anniversary Action Event   1 Event date  2 Event Link  3 Event location
    4 Hosted by:  5 Affiliate?  6 Main contact name   7 Main contact info   8 Facebook
    9 Twitter 10 Insta
    '''
    # keep these fields
    fields = {'name': 0, 'eventDate': 1, 'eventLink': 2, 'location': 3, 'host': 4,
              'affiliate': 5, 'contactName': 6, 'contactEmail': 7, 'facebook': 8,
              'twitter': 9, 'instagram': 10}
    sheet = read_sheet('Sheet1!A1:K', fields, 3, False)
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
    fields = {'name': 0, 'location': 1, 'contactName': 3, 'contactEmail': 5,
              'facebook': 9, 'twitter': 10, 'instagram': 11, 'other': 12,
              'website': 13, 'event': 14, 'eventDate': 15, 'eventLink': 16,
              'photo': 17, 'about': 18}
    return read_sheet('Sheet1!A1:S', fields, 1, True)


def get_geojson(url):
    print('\nload geojson')
    resp = requests.get('https://s3.amazonaws.com/ragtag-marchon/%s' % url)
    features = {}
    for feature in resp.json()['features']:
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
            if feature['relevance'] < 0.75:
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
            print('%s missing geometry; deleting' % key)
            del dataset[key]

    orphans = []
    for key in dataset:
        if key in sheet:
            print('%s in dataset and sheet' % key)
            continue
        orphans.append(key)
    print('%s orphans: %s' % (len(orphans), orphans))
    for key in orphans:
        del dataset[key]

    return dataset


def upload(dataset, filename):
    data = {
        'type': 'FeatureCollection',
        'features': [dataset[key] for key in dataset]
    }
    s3 = boto3.resource('s3')
    print(s3.Object('ragtag-marchon', filename).put(
        Body=json.dumps(data, indent=2),
        ContentType='application/json',
        ACL='public-read',
        Expires=(datetime.now() + timedelta(hours=6))
    ))


def resize_photo(service, file):
    print('resizing %s' % file['name'])
    width = 600
    file_ext = file['mimeType'].split('/')[1]
    filename = '%s.%s' % (file['id'], file_ext.lower())
    data = service.files().get_media(fileId=file['id']).execute()
    img = Image.open(io.BytesIO(data))
    pct = width / float(img.size[0])
    height = int((float(img.size[1]) * float(pct)))
    resized = img.resize((width, height), Image.ANTIALIAS)
    img_bytes= io.BytesIO()
    resized.save(img_bytes, format=file_ext.upper())
    img_bytes.seek(0)
    s3 = boto3.resource('s3')
    print(s3.Object('ragtag-marchon', filename).put(
        Body=img_bytes.read(),
        ContentType=file['mimeType'],
        ACL='public-read',
        Expires=(datetime.now() + timedelta(hours=24*7))
    ))
    return filename


def update_photos(dataset):
    # map filename to affiliate key
    print('\nupdate photos')
    photos = {}
    for key in dataset:
        props = dataset[key]['properties']
        if not props.get('photo', None):
            props['photoUrl'] = ''
            continue
        photos[props['photo']] = key
    try:
        service = build('drive', 'v3', developerKey=os.environ['GOOGLE_API_KEY'])
    except:
        # throws errors about file_cache is unavailable when using oauth2client
        # but seems to work fine
        pass
    query = '"%s" in parents' % os.environ['PHOTO_FOLDER_ID']
    '''
    array of
    {'kind': 'drive#file', 'id': 'abc', 'name': 'photo.jpg', 'mimeType': 'image/jpeg'}
    '''
    file_list = service.files().list(pageSize=1000, q=query).execute()['files']
    for photo in file_list:
        key = photos.get(photo['name'], None)
        if not key:
            print('%s not referenced from dataset' % photo['name'])
            continue
        if dataset[key]['properties'].get('photoUrl', None):
            continue
        try:
            url = 'https://s3.amazonaws.com/ragtag-marchon/%s' % resize_photo(service, photo)
            print('%s saved to %s' % (photo['name'], url))
            dataset[key]['properties']['photoUrl'] = url
        except:
            print('ERROR resizing photo')
            traceback.print_exc()


def lambda_handler(event=None, context=None):
    sheet = get_sheet_data()
    print('sheet=%s\n' % sheet)
    dataset = get_geojson('affiliates.json')
    print('dataset=%s\n' % dataset)
    keys = sheet.keys() - dataset.keys()
    if keys:
        get_geodata(sheet, keys)
    merge_data(sheet, dataset)
    update_photos(dataset)
    upload(dataset, 'affiliates.json')

def events_lambda_handler(event=None, context=None):
    sheet = get_event_data()
    print('sheet=%s\n' % sheet)
    dataset = get_geojson('events.json')
    print('dataset=%s\n' % dataset)
    keys = sheet.keys() - dataset.keys()
    if keys:
        get_geodata(sheet, keys)
    merge_data(sheet, dataset)
    upload(dataset, 'events.json')
