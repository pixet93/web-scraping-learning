import requests
import re
import json
from collections import OrderedDict
from bs4 import BeautifulSoup


JSON_PATH = "C:\\Users\\erik_\\Desktop\\camera_data.json"

SENSOR_AREA_PITCH_RE = r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
                       r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'

SENSOR_DIMENSION_RE = r'(?P<res_dim>[0-9]+ x [0-9]+)?(\s+)' \
        r'(?P<res_name>[a-z-A-Z0-9\.:\s]+)?(\s+)' \
        r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
        r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'

_ALLOWED_CAM_MANUFACTURERS = ['arri', 'blackmagic', 'sony']

camera_data = OrderedDict()

URL = 'https://vfxcamdb.com/'
page = requests.get(URL)
soup_query = BeautifulSoup(page.content, 'html.parser')

results = soup_query.find(id='primary')
entry_content = results.find('div', attrs={'class': 'entry-content'})
camera_section = entry_content.find(
    'p', text='Cinema and Television Cameras').next_sibling.next_sibling

for cam_manufacturer in _ALLOWED_CAM_MANUFACTURERS:
    camera_links = camera_section.find_all('a', string=lambda s: cam_manufacturer in s.lower())
    camera_data[cam_manufacturer] = OrderedDict()
    for link in camera_links:
        camera_type = link.string
        url = link.get('href')
        page = requests.get(url)
        next_soup = BeautifulSoup(page.content, 'html.parser')
        results = next_soup.find('div', attrs={'class': 'entry-content'})

        sensor_dimensions_paragraph = next(p for p in results.find_all('p')
                                           if 'sensor dimensions' in p.text.lower())
        print camera_type

        paragraph_string = sensor_dimensions_paragraph.prettify()
        paragraph_string = paragraph_string.replace(u'\xa0', ' ')
        paragraph_string = re.sub(r'\s+', ' ', paragraph_string)
        sensor_regex = re.compile(SENSOR_DIMENSION_RE)
        # If there is a camera type with multiple resolutions
        matches = [m.groupdict() for m in sensor_regex.finditer(paragraph_string)]
        if matches:
            resolution_data = OrderedDict()
            for match in matches:
                sensor_dimension_data = OrderedDict()
                dimension = match.get('res_dim')
                res_name = match.get('res_name')
                sensor_dimension_data['resolution'] = '{0} - {1}'.format(dimension, res_name)
                aperture_mm = match.get('mm')
                aperture_inches = match.get('inches')
                sensor_dimension_data['Aperture (mm)'] = aperture_mm
                sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                resolution_data[res_name] = sensor_dimension_data

            camera_data[cam_manufacturer][camera_type] = resolution_data
        else:
            pitch_regex = re.compile(SENSOR_AREA_PITCH_RE)
            # If there is a camera type with a single sensor pitch
            match = pitch_regex.search(paragraph_string)
            if match:
                resolution_data = OrderedDict()
                match_dict = match.groupdict()
                aperture_mm = match_dict.get('mm')
                aperture_inches = match_dict.get('inches')
                resolution_data['Aperture (mm)'] = aperture_mm
                resolution_data['Aperture (Inches)'] = aperture_inches
                resolution_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                camera_data[cam_manufacturer][camera_type] = resolution_data
            else:
                resolution_data = OrderedDict({'sensors': OrderedDict()})
                for paragraph in results.find_all('p'):
                    emphasis_mode = paragraph.find('em', text=lambda text: 'mode' in text.lower())
                    if not emphasis_mode:
                        continue
                    mode = emphasis_mode.string
                    paragraph_string = paragraph.prettify()
                    paragraph_string = paragraph_string.replace(u'\xa0', ' ')
                    paragraph_string = re.sub(r'\s+', ' ', paragraph_string)
                    sensor_regex = re.compile(SENSOR_DIMENSION_RE)
                    # If there is a camera type with sensor modes containing resolutions
                    matches = [m.groupdict() for m in sensor_regex.finditer(paragraph_string)]
                    if matches:
                        resolutions = OrderedDict()
                        for match in matches:
                            sensor_dimension_data = OrderedDict()
                            dimension = match.get('res_dim')
                            res_name = match.get('res_name')
                            sensor_dimension_data['resolution'] = '{0} - {1}'.format(dimension, res_name)
                            aperture_mm = match.get('mm')
                            aperture_inches = match.get('inches')
                            sensor_dimension_data['Aperture (mm)'] = aperture_mm
                            sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                            sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                            resolutions[res_name] = sensor_dimension_data
                            resolution_data['sensors'][mode] = resolutions

                camera_data[cam_manufacturer][camera_type] = resolution_data

with open(JSON_PATH, 'w') as output:
    json.dump(camera_data, output)