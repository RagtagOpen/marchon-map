""""
Functions for formatting AWS Lambda run logs
"""
import datetime
import re

def create_message_subject(info):
    """
    Create the message subject
    """
    base = '%s request completed' % info['name']
    if info['errors'] > 0:
        return '%s with ERRORS!' % base
    elif info['warnings'] > 0:
        return '%s with WARNINGS!' % base
    else:
        return base
        
def format_log_event(event):
    """
    Format an AWS lambda log event.
    """
    message = event['message']
    ts = datetime.datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%H:%M:%S')
    if message.startswith('START'):
        return '%s %-7s\n' % (ts, 'START')
    elif message.startswith('END'):
        return '%s %-7s\n' % (ts, 'END')
    elif message.startswith('REPORT'):
        return '' # ignore report events
    else:
        match = re.match(r"(?s)\[([A-Z]+)\]\s+\S+\s+\S+\s+(.+)", message)
        if match:
            result = '%s %-7s %s' % (ts,match.group(1),match.group(2))
        else:
            result =  '%s %s' % (ts, message)
        if not result.endswith('\n'):
            result = result + '\n'
        return result
    
def create_message_body(info):
    """
    Create the message body, including summary information and formatted event log.
    """
    return 'Execution results for %s\n\n' % info['name'] + \
           '%d errors\n' % info['errors'] + \
           '%d warnings\n' % info['warnings'] + \
           '\nExecution Log\n\n' + \
           ''.join(map(format_log_event, info['events'])) + \
           '\nLambda Function: %s\n' % info['function'] + \
           'Request ID: %s\n' % info['requestId'] + \
           'Started: %s\n' % datetime.datetime.fromtimestamp(info['start'] / 1000) + \
           'Duration: %f seconds' % datetime.timedelta(milliseconds=info['duration']).total_seconds()
      
if __name__ == "main":
    raise NotImplementedError('This module cannot be executed.')