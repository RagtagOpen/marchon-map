import os

import marchon

'''
    set these in environment

    GOOGLE_API_KEY
    SHEET_ID
    MAPBOX_ACCESS_TOKEN
'''
# print output instead of saving to S3
marchon.events_lambda_handler(event=None, context=None, dry_run=True)
