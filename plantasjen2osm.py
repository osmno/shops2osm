#!/usr/bin/env python
# -*- coding: utf8

# plantasjen2osm
# Converts Plantasjen garden centres from Plantasjen json api to osm format for import/update
# Usage: python plantasjen2osm.py > output_filename.osm
# Loads postal codes and municipality codes from Posten/Bring and county names from Kartverket/Geonorge


import cgi
import json
import csv
import urllib2


version = "0.1.0"


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

	# Load HTML page with shop data

	header = {
		"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
		"X-Requested-With": "XMLHttpRequest"
		}

	link = "https://www.plantasjen.no/on/demandware.store/Sites-PlantagenNO-Site/nb_NO/Stores-FindStores?showMap=undefined&radius=15000&lat=60.47202399999999&long=8.46894599999996&locationSearch=Norge"
	request = urllib2.Request(link, headers=header)
	file = urllib2.urlopen(request)
	store_data = json.load(file)

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="plantasjen2osm v%s" upload="false">' % version)

	node_id = -11000

	# Loop all stores and produce OSM file

	for store in store_data['stores']:

		node_id -= 1

		print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['latitude'], store['longitude']))

		name_split = store['name'].split("-")
		branch = name_split[len(name_split) - 1].strip()  # Use last part of store name

		make_osm_line ("shop", "garden_centre")
		make_osm_line ("ref:plantasjen", store['ID'])
		make_osm_line ("name", "Plantasjen " + branch)
		make_osm_line ("brand", "Plantasjen")
		make_osm_line ("branch", branch)
		make_osm_line ("phone", "+47 " + store['phone'])
		make_osm_line ("email", store['email'].lower())

		if branch != store['name']:
			make_osm_line ("alt_name", "Plantasjen " + store['name'])  # Include "Oslo" etc in alt_name

		address = ""
		if store['address1']:
			address += store['address1'] + ", "
		if store['address2']:
			address += store['address2'] + ", "
		postal_code = store['postalCode'].replace("\\","")
		address += postal_code + " " + store['city']

		make_osm_line ("ADDRESS", address)

		if store['postalCode'] and municipality_id[ int(postal_code) ]:
			make_osm_line("COUNTY", county_names[ municipality_id[ int(postal_code) ][0:2] ])
		elif store['postalCode'] == "3400":
			make_osm_line("COUNTY", "Buskerud")
		
		# Make array of opening hours per day. Ignore public holidays etc.

		hours = ["", "", "", "", "", "", ""]

		hours_split = store['storeHours'].split(" <br>\n")

		hours[0] = hours_split[0].replace("Hverdager ","").replace("-", ":00-") + ":00"
		hours[1] = hours[0]
		hours[2] = hours[0]
		hours[3] = hours[0]
		hours[4] = hours[0]

		hours[5] = hours_split[1].replace(u"Lørdag ","").replace("-", ":00-") + ":00"

		if hours_split[2] != u"Søndag Stengt":
			hours[6] = hours_split[2].replace(u"Søndag ","").replace("-", ":00-") + ":00"

		make_osm_line("opening_hours", get_opening_hours(hours))

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')