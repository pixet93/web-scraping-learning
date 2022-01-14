#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
#==============================================================================
# This file uses Python library BeautifulSoup (4.9.3) to pull camera preset
# data out of HTML pages from a vfx camera database: "https://vfxcamdb.com/".
# Output is serialised into JSON and then parsed into the Camera Configurator.
# NOTE: This script has been specifically written to get camera preset data.
# Changes are required in script if any other data needs to be fetched.

# HOW TO USE: Copy content of script and run outside the proxy network.
# NOTE: Any attempts to use script inside network will not work.
#==============================================================================
"""

import requests
import re
import json

from collections import OrderedDict
from bs4 import BeautifulSoup


JSON_OUTPUT_PATH = "C:\\Users\\erik_\\Desktop\\camera_data.json"

SENSOR_AREA_PITCH_RE = r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
                       r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))'
sensor_area_regex = re.compile(SENSOR_AREA_PITCH_RE)

SENSOR_DIMENSION_RE = r'(?P<res_dim>[0-9]+ x [0-9]+?([a-z-A-Z0-9\.:\s]+))(\s+)' \
        r'(?P<mm>[a-z-A-Z0-9\.]+ mm x [a-z-A-Z0-9\.]+ mm) ' \
        r'(?P<inches>\([a-z-A-Z0-9\.]+ in x [a-z-A-Z0-9\.]+ in\))?'
sensor_dimension_regex = re.compile(SENSOR_DIMENSION_RE)

# To filter other manufacturers, please update list to get them
"""_ALLOWED_CAM_MANUFACTURERS = ['Red']"""

_ALLOWED_CAM_MANUFACTURERS = ['Arri', 'Blackmagic', 'Canon', 'Panasonic',
                              'Panavision', 'Sony', 'Red', 'Vision Research']

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

        all_matches = list()
        for paragraph in results.find_all('p'):
            emphasis_mode = paragraph.find('em', text=lambda text: 'mode' in text.lower())
            if emphasis_mode:
                continue
            # The paragraph string is formatted to remove any unicode characters and extra spaces
            paragraph_string = paragraph.prettify()
            if 'Image Resolution' in paragraph_string:
                break
            if u'\xa0' in paragraph_string:
                paragraph_string = paragraph_string.replace(u'\xa0', ' ')
            if u'×' in paragraph_string:
                paragraph_string = paragraph_string.replace(u'×', 'x')
            paragraph_string = re.sub(r'\s+', ' ', paragraph_string)
            matches = [m.groupdict() for m in sensor_dimension_regex.finditer(paragraph_string)]
            all_matches.extend(matches)

        # Match a camera type that got multiple sensor resolutions
        if all_matches:
            resolution_data = OrderedDict({'Resolutions': OrderedDict()})
            for match in all_matches:
                sensor_dimension_data = OrderedDict()
                dimension = match.get('res_dim')
                aperture_mm = match.get('mm')
                aperture_inches = match.get('inches')
                sensor_dimension_data['Aperture (mm)'] = aperture_mm
                sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm, aperture_inches)
                resolution_data['Resolutions'][dimension] = sensor_dimension_data

            camera_data[cam_manufacturer][camera_type] = resolution_data
        else:
            # Match a camera type that got a single sensor pitch resolution
            sensor_dimensions_paragraph = next(p for p in results.find_all('p')
                                               if 'sensor dimensions' in p.text.lower()
                                               or 'sensor imaging area' in p.text.lower())
            emphasis_mode = sensor_dimensions_paragraph.find('em', text=lambda text: 'mode' in text.lower())

            paragraph_string = sensor_dimensions_paragraph.prettify()
            if u'\xa0' in paragraph_string:
                paragraph_string = paragraph_string.replace(u'\xa0', ' ')
            if u'×' in paragraph_string:
                paragraph_string = paragraph_string.replace(u'×', 'x')
            paragraph_string = re.sub(r'\s+', ' ', paragraph_string)

            match = sensor_area_regex.search(paragraph_string)
            if match and not emphasis_mode:
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
                            aperture_mm = match.get('mm')
                            sensor_dimension_data['Aperture (mm)'] = aperture_mm
                            aperture_inches = match.get('inches')
                            if aperture_inches:
                                sensor_dimension_data['Aperture (Inches)'] = aperture_inches
                                sensor_dimension_data['Sensor Area Pitch'] = '{0} {1}'.format(aperture_mm,
                                                                                              aperture_inches)
                            else:
                                sensor_dimension_data['Sensor Area Pitch'] = aperture_mm

                            resolutions[dimension] = sensor_dimension_data

                        resolution_data['Sensors'][sensor_mode] = resolutions

                camera_data[cam_manufacturer][camera_type] = resolution_data

# Writing scraped camera data to JSON output
with open(JSON_OUTPUT_PATH, 'w') as output:
    json.dump(camera_data, output)