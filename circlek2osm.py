#!/usr/bin/env python
# -*- coding: utf8

# circlek2osm
# Converts Circle K and Best fuel stations from json file to osm format for import/update
# Usage: circlek2osm [input_filename.json] > output_filename.osm
# Reads postal/municipality codes from Posten


import json
import cgi
import HTMLParser
import sys
import csv
import urllib2
from datetime import datetime


version = "0.3.1"

fuels = {
	'17': 'adblue',  # AdBlue
	'20': 'octane_95',  # Benzin '95
	'25': 'diesel',  # Diesel
	'30': 'ethanol',  # ED95
	'36': 'biodiesel',  # HVO100
	'38': 'lpg',  # LPG
	'40': 'octane_95',  # miles 95
	'41': 'octane_98',  # miles 98
	'42': 'diesel',  # miles Diesel
	'45': 'octane_95',  # milesPLUS 95
	'47': 'diesel',  # milesPLUS Diesel
	'50': 'taxfree_diesel'  # Anleggsdiesel
}

services = {
	'1': 'car:rental',  # Car rental
	'2': 'trailer:rental',  # Trailer rental
	'5': 'hgv',  # TruckDiesel network
	'7': 'car_wash',  # Car wash
	'8': 'car_wash',  # Car wash jetwash
	'9': 'hgv',  # Truck parking
	'51': 'fuel:propane',  # Gas
	'15': 'internet_access',  # Wifi
	'59': 'hgv'  # Truckers club
}

transform = [
	('Syd', 'syd'),
	(u'Sør', u'sør'),
	(u'Øst', u'øst'),
	('Nord', 'nord'),
	('Vest', 'vest'),
	('I', 'i'),
	('Plass', 'plass'),
	('Bru', 'bru'),
	('Gate', 'gate'),
	('Verk', 'verk'),
	('Lufthavn', 'lufthavn'),
	("Boby'N", "Boby'n"),
	('Ccb', 'CCB'),
	('Ts', '')
]

days = ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')

short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


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
		filename = sys.argv[1]

		with open(filename) as file:
			store_data = json.load(file)
			file.close()

	else:

		link = "https://www.circlek.no/cs/Satellite?pagename=CMS/Stations/SearchFilterProxy&country=no&categories=statoil+station,1-2-3+station,truck+station"
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
	print ('<osm version="0.6" generator="circlek2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['sites']:

		if store['category'] != "Best":

			node_id -= 1

			print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['lat'], store['lng']))

			# Fix name

			name = store['name'].strip().replace(".","").replace(" -",",").replace("  "," ").title()

			split_name = name.split()
			for word in transform:
				if word[0] in split_name:
					name = name.replace(word[0], word[1])
			name = name.replace("  "," ")

			branch = name.replace(store['category'],"").replace("Circle K","").replace("Automat","").replace("Truck","").strip().replace("  "," ")

			# Produce station tags

			if "Bilvask" in split_name:
				make_osm_line("amenity", "car_wash")
			else:
				make_osm_line("amenity", "fuel")

			make_osm_line("ref:circlek", str(store['id']))
			make_osm_line("name", name)
			make_osm_line("branch", branch)

			if store['category'] != "Best":
				make_osm_line("brand", "Circle K")
			else:
				make_osm_line("brand", "Best")
			
			if "street" in store:
				make_osm_line("ADDRESS", store['street'] + ", " + store['zipcode'] + " " + store['city'])
			else:
				make_osm_line("ADDRESS", store['zipcode'] + " " + store['city'])

			if (store['category'] == "1-2-3") or name.find("Automat") >= 0:
				make_osm_line("automated", "yes")

			if (name.find("Tine") >= 0) or (name.find("Posten") >= 0):
				make_osm_line("access", "private")

			# Get all fuel types

			fuel_tags = []

			for fuel in store['fuelServices']:
				found = False

				for fuel_test, fuel_tag in fuels.iteritems():
					if fuel[0] == fuel_test:
						found = True
						if not(fuel_tag in fuel_tags):
							fuel_tags.append(fuel_tag)
						break

				if not(found):
					make_osm_line ("FUEL:" + fuel[0], fuel[1])
					sys.stderr.write("New fuel type found: %s - %s" % (fuel[0], fuel[1]))

			for fuel in fuel_tags:
				make_osm_line ("fuel:" + fuel, "yes")

			# Get services

			if store['category'] == "Truck":
				service_tags = ['hgv']
			else:
				service_tags = []

			for service in store['services']:
#				make_osm_line ("service:" + service[0], service[1])

				for service_test, service_tag in services.iteritems():
					if service[0] == service_test:
						if not(service_tag in service_tags):
							service_tags.append(service_tag)
						break

			for service in service_tags:
				if service == "internet_access":
					make_osm_line(service, "wlan")
				else:
					make_osm_line(service, "yes")

			if "hgv" in service_tags:
				make_osm_line("fuel:HGV_diesel", "yes")

			# Find county from looking up postal code translation, first two digits

			if municipality_id[int(store['zipcode'])]:
				make_osm_line("COUNTY", county_names[ municipality_id[ int(store['zipcode']) ][0:2] ])
			elif store['zipcode'] == '7977':
				make_osm_line("COUNTY", u"Trøndelag")

			# Contact tags

			if 'email' in store:
				if store['email'] and (store['email'] != "No email needed"):
					make_osm_line("email", store['email'].lower().replace(",",";"))

			if 'phonenumber' in store:
				if store['phonenumber']:
					if store['phonenumber'][0] == "+":
						make_osm_line("phone", store['phonenumber'])
					else:
						make_osm_line("phone", "+" + store['phonenumber'])

			# Opening hours		
			# Make array of opening hours per day

			hours = ["", "", "", "", "", "", ""]

			if ("weekdays" in store) and ("saturdays" in store) and ("sundays" in store):
				for day in range(5):
					hours[day] = store['weekdays']
				hours[5] = store['saturdays']
				hours[6] = store['sundays']

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
				make_osm_line("FUEL", str(store['fuelServices']))
				make_osm_line("SERVICES", str(store['services']))

			# Done with OSM store node

			print('  </node>')


	# Produce OSM file footer

	print('</osm>')
