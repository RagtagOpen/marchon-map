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
        match = re.match('\[([A-Z]+)\]\t[^\t]+\t[^\t]+\t([^\n]+)\n', message)
        if match:
            return '%s %-7s %s\n' % (ts,match.group(1),match.group(2))
        else:
            return '%s %s\n' % (ts, message)
    
def create_message_body(info):
    """
    Create the message body, including summary information and formatted event log.
    """
    return 'Execution results for %s (%s)\n\n' % (info['name'], info['requestId']) + \
      'Execution time: %s seconds\n' % datetime.timedelta(milliseconds=info['duration']).total_seconds() + \
      '%d errors\n' % info['errors'] + \
      '%d warnings\n' % info['warnings'] + \
      '\nExecution Log\n\n' + \
      ''.join(map(format_log_event, info['events']))
      
if __name__ == "main":
    raise NotImplementedError('This module cannot be executed.')