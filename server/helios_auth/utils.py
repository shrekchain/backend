"""
Some basic utils 
(previously were in helios module, but making things less interdependent

2010-08-17
"""

import json

## JSON
def to_json(d):
    return json.dumps(d, sort_keys=True)


def from_json(json_data):
    if not json_data:
        return None
    try:
        json_str = json_data.decode()
    except (UnicodeDecodeError, AttributeError):
        json_str = json_data
    return json.loads(json_str)


def JSONtoDict(json):
    x = json.loads(json)
    return x


def JSONFiletoDict(filename):
    f = open(filename, "r")
    content = f.read()
    f.close()
    return JSONtoDict(content)
