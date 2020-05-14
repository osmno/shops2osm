#!/usr/bin/env python
# -*- coding: utf8

# apotek12osm
# Converts Apotek 1 pharmacies from json to osm format for import/update
# Usage: apotek12osm [input_filename.json] > output_filename.osm
# Loads json data from Apotek1 website unless an input file name is given


import json
import cgi
import HTMLParser
import sys
import urllib2


version = "0.4.0"


transform = [
	('Torv', 'torv'),
	('Torg', 'torg'),
	('Helsepark', 'helsepark'),
	('Handelspark', 'handelspark'),
	('Havn', 'havn'),
	('Stadion', 'stadion'),
	('AS', ''),
	('Senter', 'senter'),
	('Bydel', 'bydel'),
	('St', 'St.'),
	('Hus', 'hus'),
	('Park', 'park'),
	(u'Gård', u'gård'),
	('Syd', 'syd'),
	('Storsenter', 'storsenter'),
	('Helsebygg', 'helsebygg'),
	('Sentrum', 'sentrum'),
	('Apotek', 'apotek'),
	('Brygge', 'brygge'),
	('Lufthavn', 'lufthavn'),
	('Nord', 'nord'),
	('Medisinutsalg', 'medisinutsalg')
]

days = ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


# Produce a tag for OSM file

def make_osm_line(key,value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	debug = True

	# Read all data into memory

	
	if len(sys.argv) > 1:
		filename = sys.argv[1]

		with open(filename) as f:
			store_data = json.load(f)
			f.close()

	else:
		link = 'https://www.apotek1.no/wcs/resources/store/10151/storelocator/latitude/59.9139/longitude/10.7522?maxItems=1000&radiusUOM=km&radius=2500&siteLevelStoreSearch=false'
		header = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
			"X-Requested-With": "XMLHttpRequest"
			}

		request = urllib2.Request(link, headers=header)
		file = urllib2.urlopen(request)
		store_data = json.load(file)
		file.close()

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="apotek12osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['PhysicalStore']:

		node_id -= 1

		print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['latitude'], store['longitude']))

		# Fix name

		name = store['Description'][0]['displayStoreName']

		split_name = name.split()
		for word in transform:
			if word[0] in split_name:
				name = name.replace(word[0], word[1])
		name = name[0].upper() + name[1:].replace("  "," ").rstrip()

		branch = name.replace("Apotek 1 ", "")

		# Produce station tags

		make_osm_line("amenity", "pharmacy")
		make_osm_line("ref:apotek1", str(store['storeName']))
		make_osm_line("name", name)
		make_osm_line("branch", branch)
		make_osm_line("brand", "Apotek 1")

		if store['telephone1']:
			make_osm_line("phone", "+47 " + store['telephone1'])

		make_osm_line("COUNTY", store['stateOrProvinceName'])
		
		address = store['addressLine'][0].strip()
		if store['addressLine'][1].strip():
			address = address + ", " + store['addressLine'][1].strip()
		address = address + ", " + store['postalCode'].rstrip() + " " + store['city']
		make_osm_line("ADDRESS", address)

		# Make array of opening hours per day

		hours = ["", "", "", "", "", "", ""]

		for attr in store['Attribute']:
			if (attr['name'] == "email") and ("@" in attr['value']):
				make_osm_line("email", attr['value'].lower())

			if not(attr['value'] in ["STENGT", " "]):
				for day in range(7):
					if attr['name'] == "Open" + days[day] or attr['name'] == "Close" + days[day]:
						hours_value = attr['value'].replace(".", ":").replace("_", ":")
						if hours_value[-2] == ":":  # Missing zero at end
							hours_value += "0"
						if attr['name'] == "Open" + days[day]:
							hours[day] = hours_value + "-" + hours[day]
						elif attr['name'] == "Close" + days[day]:
							hours[day] = hours[day] + hours_value

		# Loop through all sequences of opening hours to simplify

		opening_hours = ""
		start = 0

		while start <= 6:

			# First loop until start of sequence
			while start < 6 and hours[start] == "":
				start += 1

			end = start

			# Then loop until end of sequence
			while end < 6 and hours[end+1] == hours[start]:
				end += 1

			if hours[start] != "":
				if start == end:
					opening_hours = opening_hours + ", " + short_days[start] + " " + hours[start]
				else:
					opening_hours = opening_hours + ", " + short_days[start] + "-" + short_days[end] + " " + hours[start]

			start = end + 1

		opening_hours = opening_hours.lstrip(", ").replace(".",":").replace("-00:00", "-24:00")

		if len(opening_hours) == 17:
			if (opening_hours == "Mo-Su 00:00-24:00") or ((opening_hours[0:5] == "Mo-Su") and (opening_hours[6:11] == opening_hours[12:17])):
				opening_hours = "24/7"

		make_osm_line("opening_hours", opening_hours)

		# For debugging/inspection
		
		if debug:
			make_osm_line("UNIQUE_ID", store['uniqueID'])

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')
	
