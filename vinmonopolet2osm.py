#!/usr/bin/env python
# -*- coding: utf8

# vinmonopolet2osm
# Converts Vinmonopolet stores from Vinmonopolet csv file to osm format for import/update
# Usage: python vinmonopolet2osm.py [input_file.csv] > output_filename.osm
# Loads postal codes and municipality codes from Posten/Bring and county names from Kartverket/Geonorge


import cgi
import json
import sys
import csv
import urllib2


version = "0.1.0"


transform_name = [
	('Torg', 'torg'),
	('Sentrum', 'sentrum'),
	('Stadion', 'stadion'),
	('Basar', 'basar'),
	('Brygge', 'brygge'),
	('Storsenter', 'storsenter'),
	('Senter', 'senter'),
	('Valkendorfsgt.', 'Valkendorfsgaten'),
	('Kiellandsplass', 'Kiellands plass'),
	('Verk', 'verk'),
	('N.', '')

]

# Produce a tag for OSM file

def make_osm_line(key,value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Produce opening_hours tag
# Argument 'hours' is a list of 7 elements contining daily opening hours "10:00-18:00", or empty if closed

def get_opening_hours (hours) :

	short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')
	opening_hours = ""
	start = 0

	# Loop all sequences of opening hours to simplify

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

	opening_hours = opening_hours.lstrip(", ")

	if len(opening_hours) == 17:
		if (opening_hours == "Mo-Su 00:00-24:00") or ((opening_hours[0:5] == "Mo-Su") and (opening_hours[6:11] == opening_hours[12:17])):
			opening_hours = "24/7"

	return opening_hours


# Main program

if __name__ == '__main__':

	# Read county names

	filename = "https://register.geonorge.no/api/sosi-kodelister/fylkesnummer.json?"
	file = urllib2.urlopen(filename)
	county_data = json.load(file)
	file.close()

	county_names = {}
	for county in county_data['containeditems']:
		if county['status'] == "Gyldig":
			county_names[county['codevalue']] = county['label'].strip()

	# Read postal codes and municipality codes from Posten (updated daily)

	file = urllib2.urlopen('https://www.bring.no/postnummerregister-ansi.txt')
	postal_codes = csv.DictReader(file, fieldnames=['zip','post_city','municipality_ref','municipality_name','type'], delimiter="\t")
	municipality_id = [None] * 10000
	for row in postal_codes:
		municipality_id[int(row['zip'])] = row['municipality_ref']
	file.close()

	# Open CSV with shop data

	if len(sys.argv) > 1:
		filename = sys.argv[1]
		file = open(filename)
	else:
		filename = "https://www.vinmonopolet.no/medias/sys_master/locations/locations/h3c/h4a/8834253946910/8834253946910.csv"
		file = urllib2.urlopen(filename)
	
	attributes = ['date','name','street','zip','city', 'post_street', 'post_zip', 'post_city', 'phone', 'category', 'latitude', 'longitude', \
					'week', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', \
					'next_week', 'next_monday', 'next_tuesday', 'next_wednesday', 'next_thursday', 'next_friday', 'next_saturday', \
					'store_id']
	stores = csv.DictReader(file, fieldnames=attributes, delimiter=";")
	next(stores)  # Read first line (column headers)

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="vinmonopolet2osm v%s" upload="false">' % version)

	node_id = -11000

	# Loop all stores and produce OSM file

	for row in stores:

		node_id -= 1

		print('  <node id="%i" lat="%s" lon="%s">' % (node_id, row['latitude'], row['longitude']))

		name = row['name'].decode('windows-1252')
		for word_from, word_to in transform_name:
			name = name.replace(word_from, word_to)

		name_split = name.split(", ")
		branch = name_split[len(name_split) - 1].strip()  # Use last part of store name
		if branch == "sentrum":
			branch == name_split[0] + " " + branch

		make_osm_line ("shop", "alcohol")
		make_osm_line ("ref:vinmonopolet", row['store_id'])
		make_osm_line ("name", "Vinmonopolet " + branch)
		make_osm_line ("brand", "Vinmonopolet")
		make_osm_line ("branch", branch)
		make_osm_line ("phone", "+47 " + row['phone'])

		if branch != name:
			make_osm_line ("alt_name", "Vinmonopolet " + name)  # Include "Oslo" etc in alt_name

		make_osm_line ("ADDRESS", "%s, %s %s" % (row['street'].decode('windows-1252').strip(), row['zip'], row['city'].decode('windows-1252')))

		if row['zip'] and municipality_id[ int(row['zip']) ]:
			make_osm_line("COUNTY", county_names[ municipality_id[ int(row['zip']) ][0:2] ])
		
		# Make array of opening hours per day. Ignore public holidays etc.

		hours = [None] * 7
		hours[0] = row['monday']
		hours[1] = row['tuesday']
		hours[2] = row['wednesday']
		hours[3] = row['thursday']
		hours[4] = row['friday']
		hours[5] = row['saturday']
		hours[6] = ""

		for i in range(7):
			if hours[i] == "Stengt":
				hours[i] = ""
			elif hours[i]:
				hours[i] = "%s:%s-%s:%s" % (hours[i][0:2], hours[i][2:4], hours[i][7:9], hours[i][9:11])

		make_osm_line("opening_hours", get_opening_hours(hours))

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')
	file.close()