# Google sheet data -> GeoJSON

## Setup

Create a Google project and get API key:

Set GOOGLE_API_KEY in environment

Install requirements

    pip install -r requirements.txt -t .

[Google API](https://developers.google.com/sheets/api/quickstart/python)

Mapbox APIs
  - [datasets](https://github.com/mapbox/mapbox-sdk-py/blob/master/docs/datasets.md#datasets)
  - [geocoding](https://github.com/mapbox/mapbox-sdk-py/blob/master/docs/geocoding.md#geocoding)


## Run

`test.py`

    import os
    import marchon

    os.environ['GOOGLE_API_KEY'] = 'Google API key'
    os.environ['SHEET_ID'] = 'Google sheet id'
    os.environ['DATASET_ID'] = 'Mapbox dataset id'
    os.environ['MAPBOX_ACCESS_TOKEN'] = 'Mapbox token with dataset:*'

    marchon.lambda_handler()
