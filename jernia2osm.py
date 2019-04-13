#!/usr/bin/env python
# -*- coding: utf8

# jernia2osm
# Converts Jernia stores from Jernia API or JSON file to OSM format for import/update
# Usage: jernia2osm [input_filename.json] > output_filename.osm
# Loads store data from Jernia API


import json
import cgi
import sys
import urllib2


version = "0.1.0"


transform = [
	('Senter', 'senter'),
	('Storsenter', 'storsenter'),
	('Torg', 'torg'),
	('Sentrum', 'sentrum'),
	('Bygg', 'bygg'),
	('Park', 'park'),
	('Syd', ''),
	(' AS', ''),
	('Avd.', ''),
	('avd.', '')
]

days = ('mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', u'lørdag', u'søndag')

short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


# Produce a tag for OSM file

def make_osm_line(key,value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	# Read all data into memory

	if len(sys.argv) > 1:
		filename = sys.argv[1]

		with open(filename) as file:
			store_data = json.load(file)
			file.close()

	else:

		link = "https://www.jernia.no/store-finder/stores.json"
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
	print ('<osm version="0.6" generator="jernia2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for county in store_data:

		for store in county['stores']:

			node_id -= 1

			if store['showOnMap'] == True:  # Skip closed stores

				# Fix name

				name = store['name'].lstrip()

#				if name == name.upper():
#					name = name[0] + name[1:].lower()

				for word in transform:
					name = name.replace(word[0], word[1])
				name = name[0].upper() + name[1:].replace("  ", " ").strip()

				print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['geoPoint']['latitude'], store['geoPoint']['longitude']))

				make_osm_line("shop", "hardware")
				make_osm_line("ref:jernia", str(store['address']['id']))
				make_osm_line("name", name)
				make_osm_line("brand", "Jernia")
				make_osm_line("branch", name.replace("Jernia ", ""))

				if 'email' in store['address']:
					if store['address']['email']:
						make_osm_line("email", store['address']['email'])
				if 'phone' in store['address']:
					if store['address']['phone']:
						make_osm_line("phone", "+47 " + store['address']['phone'].replace(" -", ";+47").replace("/", ";+47"))
				
				address = store['address']['line1']
				if "line2" in store['address']:
					address += " " + store['address']['line2']
				address += ", " + store['address']['postalCode'] + " " + store['address']['town']

				make_osm_line("ADDRESS", address)
				make_osm_line("COUNTY", county['name'])

				# Opening hours
				# Make array of opening hours per day

				hours = ["", "", "", "", "", "", ""]

				for day in store['openingHours']['specialDayOpeningList']:
					if (day['name'] in days) and ("openingTime" in day):
						hours[days.index(day['name'])] = day['openingTime']['formattedHour'] + "-" + day['closingTime']['formattedHour']


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

				opening_hours = opening_hours.lstrip(", ").replace("-00:00", "-24:00")

				if len(opening_hours) == 17:
					if (opening_hours == "Mo-Su 00:00-24:00") or ((opening_hours[0:5] == "Mo-Su") and (opening_hours[6:11] == opening_hours[12:17])):
						opening_hours = "24/7"

				make_osm_line("opening_hours", opening_hours)


				# Done with OSM store node

				print('  </node>')


	# Produce OSM file footer

	print('</osm>')