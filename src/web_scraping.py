import requests
import re
import json
from collections import OrderedDict
from bs4 import BeautifulSoup


JSON_PATH = "C:\\Users\\erik_\\Desktop\\camera_data.json"

SENSOR_AREA_PITCH_RE = r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
                       r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'
sensor_area_regex = re.compile(SENSOR_AREA_PITCH_RE)

SENSOR_DIMENSION_RE = r'(?P<res_dim>[0-9]+ x [0-9]+)(\s+)' \
        r'(?P<res_name>[a-z-A-Z0-9\.:\s]+)(\s+)' \
        r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
        r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'
sensor_dimension_regex = re.compile(SENSOR_DIMENSION_RE)

_ALLOWED_CAM_MANUFACTURERS = ['Arri', 'Blackmagic', 'Sony']

cam_db_url = 'https://vfxcamdb.com/'
web_page = requests.get(cam_db_url)
page_query = BeautifulSoup(web_page.content, 'html.parser')

# Searching from 'primary' section to find 'entry-content' class
results = page_query.find(id='primary')
entry_content = results.find('div', attrs={'class': 'entry-content'})
# From 'entry-content' class section, step by two siblings to find desired cam section
camera_section_paragraph = entry_content.find(
    'p', text='Cinema and Television Cameras').next_sibling.next_sibling

# Time to start scraping camera data from filtered manufacturers
camera_data = OrderedDict()
for cam_manufacturer in _ALLOWED_CAM_MANUFACTURERS:
    # Find all hyperlink elements to get the urls for filtered camera types
    camera_links = camera_section_paragraph.find_all(
        'a', string=lambda s: cam_manufacturer.lower() in s.lower())
    camera_data[cam_manufacturer] = OrderedDict()
    for link in camera_links:
        camera_type = link.string
        url = link.get('href')
        # Access current camera types html page
        web_page = requests.get(url)
        page_query = BeautifulSoup(web_page.content, 'html.parser')
        # Find the entry-content class to find the paragraph titled 'sensor dimensions'
        results = page_query.find('div', attrs={'class': 'entry-content'})
        try:
            sensor_dimensions_paragraph = next(p for p in results.find_all('p')
                                               if 'sensor dimensions' in p.text.lower())
        except StopIteration:
            # Stop iteration if nothing was found from the paragraphs searched
            continue
        # The paragraph string is formatted to remove any unicode characters and extra spaces
        paragraph_string = sensor_dimensions_paragraph.prettify()
        paragraph_string = paragraph_string.replace(u'\xa0', ' ')
        paragraph_string = re.sub(r'\s+', ' ', paragraph_string)
        # Match a camera type that got multiple sensor resolutions
        matches = [m.groupdict() for m in sensor_dimension_regex.finditer(paragraph_string)]
        if matches:
            resolution_data = OrderedDict({'Resolutions': OrderedDict()})
            for match in matches:
                sensor_dimension_data = OrderedDict()
                dimension = match.get('res_dim')
                res_name = match.get('res_name')
                dimension_res = '{0} - {1}'.format(dimension, res_name)
                aperture_mm = match.get('mm')
                aperture_inches = match.get('inches')
                sensor_dimension_data['Aperture (mm)'] = aperture_mm
                sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                resolution_data['Resolutions'][dimension_res] = sensor_dimension_data

            camera_data[cam_manufacturer][camera_type] = resolution_data
        else:
            # Match a camera type that got a single sensor pitch resolution
            match = sensor_area_regex.search(paragraph_string)
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
                resolution_data = OrderedDict({'Sensors': OrderedDict()})
                for paragraph in results.find_all('p'):
                    # Search for emphasis paragraph which contains sensor mode title
                    emphasis_mode = paragraph.find('em', text=lambda text: 'mode' in text.lower())
                    if not emphasis_mode:
                        continue
                    sensor_mode = emphasis_mode.string
                    # The paragraph string is formatted to remove any unicode characters and extra spaces
                    paragraph_string = paragraph.prettify()
                    paragraph_string = paragraph_string.replace(u'\xa0', ' ')
                    paragraph_string = re.sub(r'\s+', ' ', paragraph_string)
                    # Match a camera type that got sensor modes containing one or more sensor resolutions
                    matches = [m.groupdict() for m in sensor_dimension_regex.finditer(paragraph_string)]
                    if matches:
                        resolutions = OrderedDict()
                        for match in matches:
                            sensor_dimension_data = OrderedDict()
                            dimension = match.get('res_dim')
                            res_name = match.get('res_name')
                            dimension_res = '{0} - {1}'.format(dimension, res_name)
                            aperture_mm = match.get('mm')
                            aperture_inches = match.get('inches')
                            sensor_dimension_data['Aperture (mm)'] = aperture_mm
                            sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                            sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                            resolutions[dimension_res] = sensor_dimension_data
                            resolution_data['Sensors'][sensor_mode] = resolutions

                camera_data[cam_manufacturer][camera_type] = resolution_data

# Writing scraped camera data to JSON output
with open(JSON_PATH, 'w') as output:
    json.dump(camera_data, output)