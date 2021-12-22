import requests
import re
from collections import OrderedDict
from bs4 import BeautifulSoup

SENSOR_AREA_PITCH_RE = r'[0-9]+\.[0-9]+ mm x [0-9]+\.[0-9]+ mm ' \
                       r'\([0-9]+\.[0-9]+ in x [0-9]+\.[0-9]+ in\)'

REGEX = r'(?P<res_dim>[0-9]+ x [0-9]+)?(\s+)' \
        r'(?P<res_name>[a-z-A-Z0-9\.]+ ?[a-z-A-Z0-9\.]+)?(\s+)' \
        r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
        r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'

_ALLOWED_CAM_MANUFACTURERS = ['arri']

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

cam_data = OrderedDict()

for camera_type in camera_links.keys():
    camera_types = camera_links[camera_type]['camera_types']
    for cam, url in camera_types.items()[1:2]:
        page = requests.get(url)
        next_soup = BeautifulSoup(page.content, 'html.parser')
        results = next_soup.find('div', attrs={'class': 'entry-content'})
        sensor_dimensions_paragraph = next(p for p in results.find_all('p')
                                           if 'sensor dimensions' in p.text.lower())

        sensor_dimensions = dict()
        """lines = sensor_dimensions_paragraph.prettify().splitlines()
        for line in lines:
            match = re.search(FILM_APERTURE_MM_RE, line)
            if not match:
                continue
            sensor_dimensions.append(line)"""

        if not sensor_dimensions:
            sensor_modes = OrderedDict({'sensor_modes': OrderedDict()})
            for paragraph in results.find_all('p'):
                emphasis_mode = paragraph.find('em', text=lambda text: 'mode' in text.lower())
                if not emphasis_mode:
                    continue
                mode = emphasis_mode.string
                lines = paragraph.prettify().splitlines()
                for line in lines:
                    line = str(line.lstrip().replace(u'\xa0', ''))
                    match = re.search(SENSOR_AREA_PITCH_RE, line)
                    if not match:
                        continue
                    data = OrderedDict()
                    matches = re.search(REGEX, line).groupdict()
                    dimension = matches.get('res_dim')
                    res_name = matches.get('res_name')
                    data['resolution'] = '{0} - {1}'.format(dimension, res_name)
                    aperture_mm = matches.get('mm')
                    aperture_inches = matches.get('in')
                    data['Aperture (mm)'] = aperture_mm
                    data['Aperture (Inches)'] = aperture_inches
                    data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)

                    sensor_modes['sensor_modes'][mode] = data

            camera_links[camera_type]['camera_types'][cam] = sensor_modes

            print camera_links