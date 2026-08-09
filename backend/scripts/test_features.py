import os, sys
sys.path.insert(0, '../backend')
from dotenv import load_dotenv
load_dotenv()

# Test engineer_features with a sample fighter
red = {
    'fighter_id': 'test',
    'first_name': 'Islam',
    'last_name': 'Makhachev',
    'wins': 26, 'losses': 1,
    'slpm': 4.2, 'str_acc': 0.56,
    'sapm': 1.5, 'str_def': 0.68,
    'td_avg': 3.1, 'td_acc': 0.52,
    'td_def': 0.84, 'sub_avg': 0.8,
    'height_cm': 178, 'reach_cm': 180,
    'stance': 'Southpaw', 'birthday': '1991-10-27'
}
blue = {
    'fighter_id': 'test2',
    'first_name': 'Dustin',
    'last_name': 'Poirier',
    'wins': 31, 'losses': 9,
    'slpm': 5.9, 'str_acc': 0.46,
    'sapm': 4.8, 'str_def': 0.55,
    'td_avg': 1.8, 'td_acc': 0.38,
    'td_def': 0.61, 'sub_avg': 0.4,
    'height_cm': 175, 'reach_cm': 182,
    'stance': 'Orthodox', 'birthday': '1989-01-19'
}

import datetime, numpy as np

def _age(f):
    b = f.get('birthday')
    if not b: return 28.0
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(str(b)[:10])).days / 365.25
    except: return 28.0

def _wp(f):
    w = f.get('wins', 0) or 0
    l = f.get('losses', 0) or 0
    return w / (w + l) if (w + l) > 0 else 0.5

def engineer_features(red, blue):
    def s(v): return float(v) if v is not None else 0.0
    return [
        s(red.get('slpm'))    - s(blue.get('slpm')),
        s(red.get('str_acc')) - s(blue.get('str_acc')),
        s(red.get('sapm'))    - s(blue.get('sapm')),
        s(red.get('str_def')) - s(blue.get('str_def')),
        s(red.get('td_avg'))  - s(blue.get('td_avg')),
        s(red.get('td_acc'))  - s(blue.get('td_acc')),
        s(red.get('td_def'))  - s(blue.get('td_def')),
        s(red.get('sub_avg')) - s(blue.get('sub_avg')),
        _age(red) - _age(blue),
        s(red.get('reach_cm'))  - s(blue.get('reach_cm')),
        s(red.get('height_cm')) - s(blue.get('height_cm')),
        _wp(red), _wp(blue), _wp(red) - _wp(blue),
        1.0 if red.get('stance') == 'Orthodox' else 0.0,
        1.0 if blue.get('stance') == 'Orthodox' else 0.0,
        1.0 if red.get('stance') != blue.get('stance') else 0.0,
    ]

features = engineer_features(red, blue)
print(f'Features generated: {len(features)}')
print(f'Values: {features}')
print('engineer_features works locally')
