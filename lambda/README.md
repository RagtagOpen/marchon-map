# Google sheet data -> GeoJSON

## Setup

[Create a Google project and get API key](https://console.developers.google.com/project/_/apiui/apis/library)

Install requirements

    pip install -r requirements.txt -t .

## Run

set these in environment

    GOOGLE_API_KEY
    SHEET_ID
    MAPBOX_ACCESS_TOKEN
    PHOTO_FOLDER_ID
    ACTION_NETWORK_EVENTS_CAMPAIGN_ID
    ACTION_NETWORK_API_KEY

run `python test_events.py > ../events.json` to save

## reference

[Google API](https://developers.google.com/sheets/api/quickstart/python)
[Action Network API](https://actionnetwork.org/docs/v2/)

Mapbox APIs
  - [datasets](https://github.com/mapbox/mapbox-sdk-py/blob/master/docs/datasets.md#datasets)
  - [geocoding](https://github.com/mapbox/mapbox-sdk-py/blob/master/docs/geocoding.md#geocoding)
