from family_separation import events_lambda_handler

"""
    set these in environment

    GOOGLE_API_KEY
    SHEET_ID
    MAPBOX_ACCESS_TOKEN

"""

if __name__ == '__main__':
    events_lambda_handler(dry_run=True)
