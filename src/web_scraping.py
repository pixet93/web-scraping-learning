import requests
import re
import json
from collections import OrderedDict
from bs4 import BeautifulSoup

JSON_PATH = "C:\\Users\\erik_\\Desktop\\test.json"

SENSOR_AREA_PITCH_RE = r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
                       r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'

SENSOR_DIMENSION_RE = r'(?P<res_dim>[0-9]+ x [0-9]+)?(\s+)' \
        r'(?P<res_name>[a-z-A-Z0-9\.:\s]+)?(\s+)' \
        r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
        r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'

_ALLOWED_CAM_MANUFACTURERS = ['arri', 'blackmagic']

camera_links = OrderedDict.fromkeys(_ALLOWED_CAM_MANUFACTURERS, OrderedDict({'camera_types': OrderedDict()}))

URL = 'https://vfxcamdb.com/'
page = requests.get(URL)
nice_soup = BeautifulSoup(page.content, 'html.parser')

results = nice_soup.find(id='primary')
camera_content = results.find('div', attrs={'class': 'entry-content'})
cameras = camera_content.find_all('a')


for link in cameras:
    camera_type = link.string
    url = link.get('href')
    for cam_manufacturer in _ALLOWED_CAM_MANUFACTURERS:
        if cam_manufacturer in camera_type.lower():
            camera_links[cam_manufacturer]['camera_types'][camera_type] = url

for camera_type in camera_links.keys():
    camera_types = camera_links[camera_type]['camera_types']
    for cam, url in camera_types.items():
        resolution_data = OrderedDict()
        page = requests.get(url)
        next_soup = BeautifulSoup(page.content, 'html.parser')
        results = next_soup.find('div', attrs={'class': 'entry-content'})
        try:
            sensor_dimensions_paragraph = next(p for p in results.find_all('p')
                                               if 'sensor dimensions' in p.text.lower())
        except StopIteration as err:
            continue
        paragraph_string = sensor_dimensions_paragraph.prettify()
        match = re.search(SENSOR_AREA_PITCH_RE, paragraph_string)
        if match:
            resolution_data['resolutions'] = OrderedDict()
            for line in paragraph_string.splitlines():
                line = str(line.lstrip().replace(u'\xa0', ''))
                line = re.sub(r'\s+', ' ', line)
                sensor_dimension_data = OrderedDict()
                match = re.search(SENSOR_DIMENSION_RE, line)
                if not match:
                    match = re.search(SENSOR_AREA_PITCH_RE, line)
                    if not match:
                        continue
                    matches = match.groupdict()
                    aperture_mm = matches.get('mm')
                    aperture_inches = matches.get('inches')
                    sensor_dimension_data['Aperture (mm)'] = aperture_mm
                    sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                    sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                    resolution_data = sensor_dimension_data
                else:
                    matches = match.groupdict()
                    dimension = matches.get('res_dim')
                    res_name = matches.get('res_name')
                    sensor_dimension_data['resolution'] = '{0} - {1}'.format(dimension, res_name)
                    aperture_mm = matches.get('mm')
                    aperture_inches = matches.get('inches')
                    sensor_dimension_data['Aperture (mm)'] = aperture_mm
                    sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                    sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                    resolution_data['resolutions'][res_name] = sensor_dimension_data
        else:
            resolution_data['sensor_modes'] = OrderedDict()
            for paragraph in results.find_all('p'):
                emphasis_mode = paragraph.find('em', text=lambda text: 'mode' in text.lower())
                if not emphasis_mode:
                    continue
                mode = emphasis_mode.string
                lines = paragraph.prettify().splitlines()
                resolutions = OrderedDict()
                for line in lines:
                    line = str(line.lstrip().replace(u'\xa0', ''))
                    line = re.sub(r'\s+', ' ', line)
                    match = re.search(SENSOR_DIMENSION_RE, line)
                    if not match:
                        continue
                    sensor_dimension_data = OrderedDict()
                    matches = match.groupdict()
                    dimension = matches.get('res_dim')
                    res_name = matches.get('res_name')
                    aperture_mm = matches.get('mm')
                    aperture_inches = matches.get('inches')
                    sensor_dimension_data['resolution'] = '{0} - {1}'.format(dimension, res_name)
                    sensor_dimension_data['Aperture (mm)'] = aperture_mm
                    sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                    sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                    resolutions[res_name] = sensor_dimension_data
                resolution_data['sensor_modes'][mode] = resolutions

        camera_links[camera_type]['camera_types'][cam] = resolution_data


with open(JSON_PATH, 'w') as output:
    json.dump(camera_links, output)