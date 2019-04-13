#!/usr/bin/env python
# -*- coding: utf8

# yx2osm
# Converts YX/Uno-X fuel stations from json file to osm format for import/update
# Usage: yx2osm [input_filename.json] > output_filename.osm
# If no json file is given, then stations will be read from the YX html page


import json
import cgi
import HTMLParser
import sys
import urllib2
from bs4 import BeautifulSoup


version = "0.3.0"

services = {
	'AdBlue': 'fuel:adblue',
	'95 Blyfri': 'fuel:octane_95',
	'98 Blyfri': 'fuel:octane_98',
	'Farget diesel': 'fuel:taxfree_diesel',
	'Diesel': 'fuel:diesel',
	'Hydrogen': 'fuel:lpg',
	'Marina': 'boat',
	'Truck': 'hgv'
}

transform = [
	('Syd', 'syd'),
	(u'Sør', u'sør'),
	(u'Øst', u'øst'),
	('Nord', 'nord'),
	('Vest', 'vest'),
	('Plass', 'plass'),
	('Gate', 'gate'),
	('Vei', 'vei'),
	('Torg', 'torg'),
	('Storsenter', 'storsenter'),
	(u'Gård', u'gård'),
	('(Automat)', ''),
	('(automat)', ''),
	('(YX', ''),
	('Automat)', ''),
	('(Hydrogenstasjon)', ''),
	('(Rema)', ''),
	('(7-Eleven)', '')
]


# Produce a tag for OSM file

def make_osm_line(key,value):
    if value:
		parser = HTMLParser.HTMLParser()
		value = parser.unescape(value)
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		print ('    <tag k="' + key + '" v="' + encoded_value + '" />')


# Main program

if __name__ == '__main__':

	debug = True

	# Read all data into memory
	
	if len(sys.argv) > 1:
		# Read json file

		filename = sys.argv[1]
		with open(filename) as f:
			file_content = f.read().replace("&quot;",'"').replace("&amp;","&")
			store_data = json.loads(file_content)
			f.close()

	else:
		# Load HTML page with store data

		link = "https://yx.no/privat/ruteplanlegger/"
		header = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
			"X-Requested-With": "XMLHttpRequest"
			}

		request = urllib2.Request(link, headers=header)
		page = urllib2.urlopen(request)

		datasoup = BeautifulSoup(page, features="html.parser")
		store_data = datasoup.find('body').find(class_='page').find('main').find('div').find('div').find('div').find('section')['data-stations']
		store_data = json.loads(store_data.replace("&quot;",'"').replace("&amp;","&"))

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="yx2osm v%s" upload="false">' % version)

	node_id = -17000

	# Loop through all stores and produce OSM tags

	for entry in store_data:

		store = entry['data']

		node_id -= 1

		latitude, longitude = store['geolocation'].split(",")
		print('  <node id="%i" lat="%s" lon="%s">' % (node_id, latitude, longitude))

		# Fix name

		name = store['name']

		if name[0:11] == "YX 7-Eleven":
			brand = "YX 7-Eleven"
		elif name[0:2] == "YX":
			brand = "YX"
		elif name[0:5] == "Uno-X":
			brand = "Uno-X"
		else:
			brand = ""

		name = name.replace("7-Eleven ","")

		split_name = name.split()
		for word in transform:
			if word[0] in split_name:
				name = name.replace(word[0], word[1])
		name = name.replace("  "," ").strip()

		branch = name.replace("YX ","").replace("Uno-X ","").replace("Truck ","")

		# Produce station tags

		make_osm_line("amenity", "fuel")
		make_osm_line("ref:yx", str(store['id']))
		make_osm_line("name", name)
		make_osm_line("branch", branch)
		make_osm_line("brand", brand)

		if (store['stationType'] == "unox-automat") or name.find("automat") >= 0:
			make_osm_line("automated", "yes")
		elif store['stationType'] == "yx-seven-eleven":
			make_osm_line("shop", "yes")
		
		if "address" in store:
			make_osm_line("ADDRESS", store['address'] + ", " + store['postcode'] + " " + store['city'])
		else:
			make_osm_line("ADDRESS", store['postcode'] + " " + store['city'])

		make_osm_line("COUNTY", store['county'])
		make_osm_line("MODIFIED", entry['modifiedTime'][0:10])

		# Contact tags

		if ('email' in store) and ("@" in store['email']):
			make_osm_line("email", store['email'].replace(",",";").replace("/",";").replace(" ","").rstrip("; ").strip())

		if 'phone' in store:
			phone = store['phone']
			if phone == "4212":
				phone = "04212"
			phone_length = len(phone)
			i = 0
			while (i < phone_length) and (phone[i] in ["0","1","2","3","4","5","6","7","8","9"," "]):
				i += 1
			if phone[0:i].strip():
				make_osm_line("phone", "+47 " + phone[0:i].rstrip())

		# Get services

		if name.find("Truck") >= 0:
			service_tags = ['hgv']
		else:
			service_tags = []

		if store['services'] == "Hydrogen":
			service_tags.append("fuel:lpg")
		else:
			for service in store['services']:
				if service:
#					make_osm_line ("service:" + service, "yes")

					for service_test, service_tag in services.iteritems():
						if service == service_test:
							if not(service_tag in service_tags):
								service_tags.append(service_tag)
							break

		for service in service_tags:
			make_osm_line(service, "yes")

		if "hgv" in service_tags:
			make_osm_line("fuel:HGV_diesel", "yes")

		# For debugging/inspection

		if debug:
			make_osm_line("SERVICES", str(store['services']))
			make_osm_line("STATION_TYPE", store['stationType'])

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')