# March On map

Draw March On affilates on a [Mapbox map](https://www.mapbox.com),
for embedding on [March On](https://www.wearemarchon.org).

## Google Sheets to GeoJSON

Mapbox GL JS doesn't allow access to the entire feature set, only features in the current view (https://github.com/mapbox/mapbox-gl-js/issues/2481). This map has a small number of features, and we need access to all of them to find the nearest to a user's location. Run an AWS Lambda script daily to get data from a Google sheet and save as GeoJSON on S3.

[AWS Lambda function](https://github.com/RagtagOpen/marchon-map/blob/master/lambda/marchon.py) creates GeoJSON from a Google sheet:
  - get data from Google Sheets via Google API
  - get GeoJSON from public S3 URL
  - geocode locations with Mapbox's Geocoder API
  - write GeoJSON to S3

### deploying to AWS Lambda

The image resizing code uses [Pillow](https://github.com/python-pillow/Pillow), which contains platform-specific C code. When deploying, make sure you include the Linux version in the zip file. The easiest way to do this is to create the deployment package on Linux; [get a Docker container](https://medium.freecodecamp.org/escaping-lambda-function-hell-using-docker-40b187ec1e48) if you don't have access to a Linux box. Alternatively, you can `pip install Pillow -t linux-pillow` on Linux, then copy the resulting packages into the zip. You can do this just once, then freshen `marchon.py` as needed.

create directory for Linux deployment package

    mkdir lambda-linux
    mkdir lambda-linux/lambda
    cp lambda/marchon.py lambda/requirements.txt lambda-linux/lambda

run Ubuntu docker container with python 3.6

    docker run -v /path-to/marchon-map/lambda-linux:/lambda-linux -it --rm tomersha/docker-ubuntu-14.04-python-3.6.2

activate python 3.6, install zip, install packages, and create zip

    pyenv shell 3.6.2
    apt-get install zip
    cd lambda-linux/lambda
    pip install -r requirements.txt -t .
    zip ../linux-lambda.zip -r .
    exit

upload `linux-lambda.zip` to AWS

## GeoJSON to map

[map.js](https://github.com/RagtagOpen/marchon-map/blob/master/map.js) uses Vue.js and Mapbox GL JS to create the map.

- create Mapbox GL map with MarchOn's custom style
- load GeoJSON with affiliate data from S3 (updated daily by Lambda function)
- request user's location; if available zoom map to closest affiliate
- zoom to closest affiliate on results from [Mapbox Geocoder control](https://github.com/mapbox/mapbox-gl-geocoder)
- use [Haversine formula](https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula) to find closest affiliate
- show nearest/clicked/moused over affiliate info in card to the right of map

## local setup

### Google sheet to GeoJSON (python)

Clone this repo and get python 3.6 set up.

[Create a Google project and get API key](https://console.developers.google.com/project/_/apiui/apis/library)

Set these in environment

    GOOGLE_API_KEY
    SHEET_ID
    MAPBOX_ACCESS_TOKEN

From the `lambda` directory:

  - install requirements: `pip install -r requirements.txt -t .`
  - run `python test_events.py > ../events.json`


### map (Vue.js)

Run a local web server: `python -m SimpleHTTPServer`

Go http://localhost:8000 in browser

To load a different GeoJSON data file, edit `const geojson = pegasus(`https://s3.amazonaws.com/ragtag-marchon/${mapjs.getAttribute('data-filename')}`);` in [map.js](map.js)
