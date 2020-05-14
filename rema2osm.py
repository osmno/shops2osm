#!/usr/bin/env python
# -*- coding: utf8

# rema2osm
# Converts Rema 1000 stores from Rema API or JSON file to OSM format for import/update
# Usage: rema2osm [input_filename.json] > output_filename.osm
# Loads store data from Rema API


import json
import cgi
import sys
import urllib2


version = "0.2.2"


transform = [
	('Brygge', 'brygge'),
	('Torg', 'torg'),
	('Park', 'park'),
	('Gate', 'gate'),
	('Kvartal', 'kvartal'),
	('Verk', 'verk'),
	('Senter', 'senter'),
	('Storsenter', 'storsenter'),
	('Sentrum', 'sentrum'),
	('Stadion', 'stadion'),
	('Stasjon', 'stasjon'),
	('Stasjonsby', 'stasjonsby'),
	(u'Næringspark', u'næringspark'),
	('AMFI', 'Amfi'),
	('Krohgsgate', 'Krohgs gate'),
	('Meyersgate', 'Meyers gate'),
	('Prinsensgate', 'Prinsens gate'),
	('Treschowsgate', 'Treschows gate'),
	('Tordenskjoldsgate', 'Tordenskjolds gate'),
	('Tryggvasonsgate', 'Tryggvasons gate'),
	('Hove39', 'Hov E39'),
	('Oti', 'OTI'),
	(u'Øst', u'øst'),
	(u'Sør', u'sør')
]

days = ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')

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

		link = "https://www.rema.no/api/v2/stores/"
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
	print ('<osm version="0.6" generator="rema2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['results']:

		node_id -= 1

		if store['shortName'].find("Stengt") < 0:  # Skip closed stores

			# Fix name

			name = store['shortName'].rstrip("*").lstrip()

			if name == name.upper():
				name = name[0] + name[1:].lower()
			name = name.title()

			for word in transform:
				name = name.replace(word[0], word[1])
			name = name[0].upper() + name[1:]

			print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['latitude'], store['longitude']))

			make_osm_line("shop", "supermarket")
			make_osm_line("ref:rema", str(store['id']))
			make_osm_line("name", "Rema 1000 " + name)
			make_osm_line("brand", "Rema 1000")
			make_osm_line("branch", name)

			if 'email' in store:
				if store['email']:
					make_osm_line("email", store['email'])
			if 'phone' in store:
				if store['phone']:
					make_osm_line("phone", "+47 " + store['phone'])
			
			make_osm_line("ADDRESS", store['visitAddress'] + ", " + store['visitPostCode'] + " " + store['visitPlaceName'])
			make_osm_line("COUNTY", store['countyName'])

			# Extra services

			if store['hasPostInStore'] == "true":
				make_osm_line('service:posten', 'yes')


			# Opening hours
			# Make array of opening hours per day

			hours = ["", "", "", "", "", "", ""]

			for day, time in store['openingHours'].items():
				if day in days and time != "Stengt":
					hours[days.index(day)] = time.replace(u"–","-")


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
