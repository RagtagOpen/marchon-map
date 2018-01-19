"""
Unit tests for execution monitoring code
"""

import unittest
import json
import gzip
import base64
import io

import monitor_lambda_runs as uut

# test data

test_subscription_event = { 
   'logStream': '2018/01/04/[$LATEST]610fa3c1703d4ac4975ce6375d918c69', 
   'messageType': 'DATA_MESSAGE', 
   'logEvents': [ 
       { 'extractedFields':  { 'dummy': 'RequestId:', 'type': 'END', 'requestId': '1844c0df-f186-11e7-92ed-29e116819200' }, 
         'timestamp': 1515097568250, 
         'message': 'END RequestId: 1844c0df-f186-11e7-92ed-29e116819200\n', 
         'id': '33787804820456610596729582913350286578116803276340658177' }, 
       { 'extractedFields': { 'dummy': 'RequestId:', 'type': 'END', 'requestId': 'f65dbf9d-f186-11e7-a442-2f62625222a6' }, 
         'timestamp': 1515097568871, 
         'message': 'END RequestId: f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
        'id': '33787804834305373365017099884243967625431435771554496517' },
       { 'extractedFields': { 'dummy': 'RequestId:', 'type': 'END', 'requestId': '7fd0c2ca-f18d-11e7-98dc-6d74fadb1fba' }, 
         'timestamp': 1515097569546, 
         'message': 'END RequestId: 7fd0c2ca-f18d-11e7-98dc-6d74fadb1fba\n', 
         'id': '33787804849358376374025270504780577459469079788091277321' } 
    ], 
   'owner': '187976421381', 
   'subscriptionFilters': [ 'LambdaStream_monitor-lambda-logs' ], 
   'logGroup': '/aws/lambda/hello-world' 
}

test_lambda_events = [
    { 
      'timestamp': 1515097568871, 
      'message': 'START RequestId: f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },
    { 
      'timestamp': 1515097569871, 
      'message': '[WARNING] 1515097569871 f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },
    { 
      'timestamp': 1515097570871,
      'message': '[WARNING] 1515097570871 f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },
    { 
      'timestamp': 1515097571871, 
      'message': '[INFO] 1515097571871 f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },
    { 
      'timestamp': 1515097572871, 
      'message': '[WARNING] 1515097572871 f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },
    { 
      'timestamp': 1515097573871, 
      'message': '[ERROR] 1515097573871 f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },    
    { 
      'timestamp': 1515097574871, 
      'message': 'END RequestId: f65dbf9d-f186-11e7-a442-2f62625222a6\n', 
    },

]

def compress_string(str):
    return base64.b64encode(gzip.compress(str.encode()))

def pack_subscription_event(event):
    return { 'awslogs': { 'data': compress_string(json.dumps(event)) } }

class MonitoringTests(unittest.TestCase):

    def test_decompress_data(self):
        original = 'ABCDEFGHIJKLMNOP'
        encoded = compress_string(original) # 'H4sIAFmkV1oAA3N0cnZxdXP38PTy9vH18w8AAE3/6OAQAAAA'
        result = uut.decompress_string(encoded)
        self.assertEqual(result, original)   
    
    def test_unpack_subscription_event(self):
        packed = pack_subscription_event(test_subscription_event)
        result = uut.unpack_subscription_event(packed)
        self.assertEqual(result, test_subscription_event)
    
    def test_get_request_ids(self):
        events = test_subscription_event['logEvents']
        result = uut.get_request_ids(events)
        self.assertSetEqual(set(result), {
            '1844c0df-f186-11e7-92ed-29e116819200',
            '7fd0c2ca-f18d-11e7-98dc-6d74fadb1fba',
            'f65dbf9d-f186-11e7-a442-2f62625222a6'
          })
        
    def test_analyze_run_events(self):
        result = uut.analyze_run_events(test_lambda_events)
        self.assertDictEqual(result, {
            'duration': 6000,
            'errors': 1,
            'warnings': 3                        
            })
        
    def test_create_topic_message(self):
        info = {
            'name': 'Hello World',
            'requestId': 'f65dbf9d-f186-11e7-a442-2f62625222a6',
            'duration': 6000,
            'errors': 1,
            'warnings': 3,
            'events': test_lambda_events
            }
        (subject,message) = uut.create_topic_message(info)
        self.assertRegex(subject, '''^Hello World request completed with ERRORS.+''')
        self.assertRegex(message, '''Execution results for Hello World''')                    
    
if __name__ == '__main__':
    unittest.main()