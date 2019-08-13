#!/usr/bin/env python
# -*- coding: utf8

# esso2osm
# Converts Esso fuel stations from json file to osm format for import/update
# Usage: esso2osm [input_filename.json] > output_filename.osm
# If no input file is given, data will be loaded from Esso api
# Reads postal/municipality codes from Posten, and county names from Kartverket


import json
import cgi
import HTMLParser
import csv
import urllib2
import sys

version = "0.5.0"

services = [
	('Bilvask', 'car_wash'),
	('Bilreparasjon', 'service:vehicle:car_repair'),
	('Truck', 'hgv'),
	('Minibank', 'atm'),
	('Ubetjent', 'automated'),
	('AdBlue', 'fuel:adblue'),
	('Propan', 'fuel:propane'),
	('Avgiftsfri', 'fuel:taxfree_diesel'),
	('98', 'fuel:octane_98'),
	('95', 'fuel:octane_95'),
	('Diesel', 'fuel:diesel'),
]

days = ('Mandag','Tirsdag','Onsdag','Torsdag','Fredag',u'Lørdag',u'Søndag')

short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


# Produce a tag for OSM file

def make_osm_line(key,value):
    if value:
		parser = HTMLParser.HTMLParser()
		value = parser.unescape(value)
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	debug = True

	# Read all data into memory
	
	if len(sys.argv) > 1:
		filename = sys.argv[1]

		with open(filename) as file:
			store_data = json.load(file)
			file.close()

	else:

		link = "https://www.essofuelfinder.no/nb-no/api/v1/Retail/retailstation/GetStationsByBoundingBox?latitude1=74&longitude1=-3&latitude2=55&longitude2=38"
		header = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
			"X-Requested-With": "XMLHttpRequest"
			}

		request = urllib2.Request(link, headers=header)
		file = urllib2.urlopen(request)
		store_data = json.load(file)
		file.close()

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

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="esso2osm v%s" upload="false">' % version)

	node_id = -16000

	# Loop through all stores and produce OSM tags

	for store in store_data:

		if store['LocationID'] != "100358172":  # Office, not fuel station

			node_id -= 1

			print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['Latitude'], store['Longitude']))

			# Produce station tags

			if store['DisplayName']:
				name = store['DisplayName'].encode("utf-8").decode("utf-8")
				name = name.replace("2","").replace("3","").title()
			elif store['LocationID'] == "100356373":
				name = "Grubhei"
			else:
				name = ""

			make_osm_line("amenity", "fuel")
			make_osm_line("ref:esso", store['LocationID'])
			make_osm_line("name", "Esso " + name)
			make_osm_line("branch", name)
			make_osm_line("brand", "Esso")
			
			address = store['AddressLine1'] + ", " + store['PostalCode'] + " " + store['City']
			address = address.encode("utf-8").decode("utf-8")
			make_osm_line("ADDRESS", address)

			# Get services

			service_tags = []
			service_debug = []

			for service in store['StoreAmenities'] + store['FeaturedItems']:
				service_name = service['Name'].encode("utf-8").decode("utf-8")
				service_debug.append(service_name)

				for service_test in services:
					if service_name.find(service_test[0]) >= 0:
						if not(service_test[1] in service_tags):
							service_tags.append(service_test[1])
						break

			for service in service_tags:
				make_osm_line(service, "yes")
			
			if "hgv" in service_tags:
				make_osm_line("fuel:HGV_diesel", "yes")

			# Find county from looking up postal code translation, first two digits

			if municipality_id[int(store['PostalCode'])]:
				make_osm_line("COUNTY", county_names[ municipality_id[ int(store['PostalCode']) ][0:2] ])
			elif store['PostalCode'] == "3250":
				make_osm_line("COUNTY", "Vestfold")

			# Contact tags

			if store['Telephone']:
				make_osm_line("phone", "+47 " + store['Telephone'])

			# Opening hours

			opening_hours = store['WeeklyOperatingHours'].encode("utf-8").decode("utf-8")

			if opening_hours == u"Døgnåpent":
				opening_hours = "24/7"
			else:
				split_hours = opening_hours.split(" ; ")
				opening_hours = ""
				for part in split_hours:
					if (part.find(" -") < 0) and (part.find("stengt") < 0):
						for day in range(7):
							part = part.replace(days[day], short_days[day])
						opening_hours = opening_hours + part.replace("-00:00","-24:00").replace(u"Døgnåpent", "00:00-24:00") + ", "
				opening_hours = opening_hours.rstrip(", ")

			make_osm_line("opening_hours", opening_hours)

			# For debugging/inspection

			if debug:
				make_osm_line("OPENING_HOURS", store['WeeklyOperatingHours'].encode("utf-8").decode("utf-8"))
				make_osm_line("SERVICES", str(service_debug))

			# Done with OSM store node

			print('  </node>')

	# Produce OSM file footer

	print('</osm>')
	
