import json
import os
import pytz
import datetime
from zeep import Client
from zeep.plugins import HistoryPlugin
from pyproj import Proj, transform
from apscheduler.schedulers.blocking import BlockingScheduler
from azure.storage.blob import BlobClient

client = None
history  = HistoryPlugin()

OCITC_USER = os.environ.get('OCIT_USER')
OCITC_PW = os.environ.get('OCIT_PASSWORD')

conn_str = os.environ.get('AZURE_CONN_STR')
container_name = os.environ.get('AZURE_CONTAINER_NAME')
blob_name = os.environ.get('AZURE_BLOB_NAME')
blob = BlobClient.from_connection_string(conn_str=conn_str, container_name=container_name, blob_name=blob_name)

TIMEZONE = pytz.timezone("Europe/Berlin")

MARKER_STREET = '$StraßeD$'
MARKER_SECTION = '$AbschnittD$'
MARKER_CONTENT = '$InhaltD$'

inProj = Proj('EPSG:25833')
outProj = Proj('EPSG:4326')

sched = BlockingScheduler()

def get_client():
    global client
    global history
    if client is None:
        client = Client("http://vizconcs2.concert.viz/OCIT_CSOAP?wsdl=OCIT_CIfService.wsdl", plugins=[history])
    return client.service


def get_datasets_from_ocit(objectType):
    print('Load: '+objectType)
    res = load_datasets_from_ocit(objectType)
    
    if(res["errorCode"] != 0):
        raise Exception("Server responded with error: " + str(res))

    if("dataList" not in res):
        raise Exception("Unexpected response - no data list found" + str(res))

    print('Anzahl DS: '+str(len(res["dataList"]["ds"])))

    entries = []

    for ds in res['dataList']['ds']:
        data = ds['data']
        description = data['description'][0]
        id = data['admin']['id']
        subtype = data['admin']['subtype']
        severity = data['admin']['severity']

        valid_from = None
        valid_to = None
        sort_key = None
        is_valid = True
        for validity in data['validity']:
            if validity['kind'] == 'validity':
                valid_from = validity['from'].astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M")
                sort_key = validity['from'].astimezone(TIMEZONE)
                if not validity['until'] == None:
                    valid_to = validity['until'].astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M")
                    is_valid = validity['until'].astimezone(TIMEZONE) >= TIMEZONE.localize(datetime.datetime.now())

        if is_valid:
            locations = []
            if len(data['location']) > 0:
                location = data['location'][0]
                direction = location['roaddescription']['direction']
                if direction == 'oneSided':
                    direction = 'Einseitig'
                elif direction == 'doubleSided':
                    direction = 'Beidseitig'
                for co_description in location['co_description']:
                    coordinates = []
                    for co in co_description['co']:
                        y, x = transform(inProj,outProj,co['x'],co['y'])
                        coordinates.append({
                            'x': x,
                            'y': y
                        })
                    locations.append(coordinates)
            entries.append({
                'id': id,
                'subtype': subtype,
                'severity': severity,
                'description': description,
                'validity': {
                    'from': valid_from,
                    'to': valid_to
                },
                'direction': direction,
                'locations': locations,
                'sort_key': sort_key
            })
    print("valid Entries: "+str(len(entries)))
    return entries

def load_datasets_from_ocit(objectType):
    global history
    global OCITC_USER
    global OCITC_PW
    res = get_client().inquireAll(
        userName= OCITC_USER,
        passWord= OCITC_PW,
        objectType=objectType)
    return res

def transform_to_geojson(ocit_entries):
    geojson = {
        'type': 'FeatureCollection',
        'name': 'baustellen',
        'features': []}
    for entry in ocit_entries:
        feature = {'type': 'Feature'}
        feature['properties'] = {
            'id': entry['id'],
            'subtype': entry['subtype'],
            'severity': entry['severity'],
            'validity': entry['validity'],
            'direction': entry['direction'],
            'icon': 'warnung'
        }
        if entry['subtype'] == 'Baustelle' or entry['subtype'] == 'Bauarbeiten':
            feature['properties']['icon'] = 'baustelle'
        elif entry['subtype'] == 'Sperrung':
            feature['properties']['icon'] = 'sperrung'
        pos_street = entry['description'].find(MARKER_STREET)
        pos_section = entry['description'].find(MARKER_SECTION)
        pos_content = entry['description'].find(MARKER_CONTENT)
        if pos_street > -1 and pos_section > -1:
            feature['properties']['street'] = entry['description'][pos_street+len(MARKER_STREET): pos_section].strip()
        if pos_section > -1 and pos_content > -1:
            feature['properties']['section'] = entry['description'][pos_section+len(MARKER_SECTION): pos_content].strip()
        if pos_content > -1:
            feature['properties']['content'] = entry['description'][pos_content+len(MARKER_CONTENT): ].strip()
        if len(entry['locations']) == 1:
            location = entry['locations'][0]
            if len(location) > 1:
                type = 'LineString'
                geometry = {'type': type, 'coordinates': []}
                for coord in location:
                    geometry['coordinates'].append([coord['x'],coord['y']])
                feature['geometry'] = geometry
            else:
                type = 'Point'
                geometry = {'type': type, 'coordinates': []}
                for coord in location:
                    geometry['coordinates'] = [coord['x'],coord['y']]
                feature['geometry'] = geometry
        else:
            feature['geometry'] = {'type': 'GeometryCollection', 'geometries': []}
            for location in sorted(entry['locations'], key=len):
                if len(location) > 1:
                    type = 'LineString'
                    geometry = {'type': type, 'coordinates': []}
                    for coord in location:
                        geometry['coordinates'].append([coord['x'],coord['y']])
                    feature['geometry']['geometries'].append(geometry)
                else:
                    type = 'Point'
                    geometry = {'type': type, 'coordinates': []}
                    for coord in location:
                        geometry['coordinates'] = [coord['x'],coord['y']]
                    feature['geometry']['geometries'].append(geometry)
        geojson['features'].append(feature)
    return geojson

@sched.scheduled_job('interval', minutes=10)
def import_job():
        print(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ") + ' - Run Import')
        entries = get_datasets_from_ocit('TrafficMessage_RoadWorks')
        entries += get_datasets_from_ocit('TrafficMessage_Incidents')
        entries.sort(key=lambda entry: entry['sort_key'], reverse=True)
        geojson = transform_to_geojson(entries)

        with open("./baustellen_sperrungen.json", encoding="utf-8", mode="w") as out_file:
            json.dump(geojson, indent=4, sort_keys=False, ensure_ascii=False, fp=out_file)
        with open("./baustellen_sperrungen.json", mode="rb") as out_file:
            blob.upload_blob(out_file, overwrite=True)

import_job()
sched.start()
