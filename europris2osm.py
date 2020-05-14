#!/usr/bin/env python
# -*- coding: utf8

# europris2osm
# Converts Apotek 1 pharmacies from json to osm format for import/update
# Usage: apotek12osm [input_filename.json] > output_filename.osm
# Loads json data from Apotek1 website unless an input file name is given


import json
import cgi
import HTMLParser
import sys
import urllib2


version = "0.2.0"


transform = [
	('Nord', 'nord'),
	('I', 'i')
]


short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


# Produce a tag for OSM file

def make_osm_line(key,value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	# Read all data into memory

	
	if len(sys.argv) > 1:
		filename = sys.argv[1]

		with open(filename) as f:
			store_data = json.load(f)
			f.close()

	else:
		link = 'https://www.europris.no/storestock/index/getStoresDetails'
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
	print ('<osm version="0.6" generator="europris2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['data']:

		node_id -= 1

		print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['latitude'], store['longitude']))

		# Fix name

		name = store['store_name'].title()

		split_name = name.split()
		for word in transform:
			if word[0] in split_name:
				name = name.replace(word[0], word[1])
		name = name[0].upper() + name[1:].replace("  "," ").rstrip()

		branch = name.replace("Europris ", "")

		# Produce store tags

		make_osm_line("shop", "general")
		make_osm_line("ref:europris", store['store_identifier'])
		make_osm_line("name", name)
		make_osm_line("branch", branch)
		make_osm_line("brand", "Eurorpris")

		if store['store_phone']:
			make_osm_line("phone", "+47 " + store['store_phone'].strip(", ").replace(", ", ";+47 ").replace(",", ";+47 "))

		if store['store_email']:
			make_osm_line("email", store['store_email'])

		if store['facebook_url']:
			position = store['facebook_url'].find("?")
			if position >= 0:
				make_osm_line("facebook", store['facebook_url'][0:position])
			else:
				make_osm_line("facebook", store['facebook_url'])

		make_osm_line("COUNTY", store['state'])
		make_osm_line("MUNICIPALITY", store['district'])
		
		address = store['address'].strip() + ", " + store['postal_code'].rstrip() + " " + store['city']
		make_osm_line("ADDRESS", address)

		# Make array of opening hours per day

		hours = ["", "", "", "", "", "", ""]

		hours[0] = store['open_hours_workdays'][0:5].replace(u"–","-").replace("-", ":00-") + ":00"
		hours[1] = hours[0]
		hours[2] = hours[0]
		hours[3] = hours[0]
		hours[4] = hours[0]

		if store['open_hours_saturday'] and (store['open_hours_saturday'] != "Stengt"):
			hours[5] = store['open_hours_saturday'][0:5].replace(u"–","-").replace("-", ":00-") + ":00"

		if store['open_hours_sunday'] and (store['open_hours_sunday'] != "Stengt"):
			hours[6] = store['open_hours_sunday'][0:5].replace(u"–","-").replace("-", ":00-") + ":00"

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

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')
