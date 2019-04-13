#!/usr/bin/env python
# -*- coding: utf8

# shell2osm
# Converts Shell/St1 stores from St1 json file to osm format for import/update
# Usage: shell2osm [input_filename.json] > output_filename.osm
# Default file name is st1.json, copied from Shell/St1 web page
# Reads postal/municipality codes from Posten, and county names from Kartverket


import json
import cgi
import HTMLParser
import sys
import csv
import urllib2
from datetime import datetime


version = "0.2.0"

countries = {
	'norway': '+47',
	'sweden': '+46',
	'finland': '+358'
}

fuels = [
	('rex', 'biodiesel'),
	('20', 'e20'),
	('35', 'e35'),
	('85', 'e85'),
	('95', 'octane_95'),
	('98', 'octane_98'),
	('mpo', 'taxfree_diesel'),
	('color', 'taxfree_diesel'),
	('truckdiesel', 'HGV_diesel'),
	('truckfueling', 'HGV_diesel'),
	('twoqualitydiesel', 'HGV_diesel'),
	('adblue', 'adblue'),
	('parafin', 'parafin'),
	('ethanol', 'ethanol'),
	('diesel', 'diesel'),
	('vpower', 'octane_95')  # For "vpower" without any other coding
]

services = [
	('carwash', 'car_wash'),
	('handwash', 'car_wash'),
	('coffee', 'cafe'),
	('helmisimpukka', 'cafe'),
	('toilet', 'toilets'),
	('boutique', 'shop'),
	('fastfood', 'fast_food'),
	('burgerking', 'fast_food'),
	('post', 'post_office'),
	('carmaintenance', 'service:vehicle:car_repair'),
	('trailer', 'trailer:rental'),
	('mobilefuleing', 'payment:app')
]

transform = [
	('Storbilsenter', 'storbilsenter'),
	('Syd', 'syd'),
	(u'Øst', u'øst'),
	('Nord', 'nord'),
	('Vest', 'vest'),
	('I', 'i'),
	('Veikro', 'veikro'),
	('Billag', 'billag'),
	('Verk', 'verk'),
	('Hafstadvn', 'Hafstadvegen'),
	('Crt', 'CRT')
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


# Fetch country from string

def get_country(code):

	global station_country
	global countries

	for country in countries:
		if code.find(country) >= 0:
			station_country = country


# Main program

if __name__ == '__main__':

	debug = True

	# Read all data into memory
	
#	filename = "st1.json"

	if len(sys.argv) > 1:
		filename = sys.argv[1]
		with open(filename) as file:
			store_data = json.load(file)
			file.close()

	else:
		url = "https://placelocator.st1.fi/api/v1/find-places/area"

		header = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.2 Safari/605.1.15",
			"Accept": "application/json, text/plain, */*",
			"Content_type": "application/json",
			"Origin": "https://www.st1.no",
			"Accept-Language": "nb-no",
			"Host": "placelocator.st1.fi",
			"Conncection": "keep-alive",
			"Referer": "https://www.st1.no/stasjoner/",
			"Accept-Encoding": "br, gzip, deflate",
			"x-api-key": "frontkey"
			}

		query_data = '{"northWestLatitude":72.31313239353962,"northWestLongitude":-64.67176037500008,"southEastLatitude":46.24980839536913,"southEastLongitude":96.87120837499992,"searchQuery":"","filters":{}}'

		request = urllib2.Request(url, data=query_data, headers=header)
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
	print ('<osm version="0.6" generator="rema2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['stations']:

		if len(store['postcode']) == 4:  # Norwegian stations

			node_id -= 1

			# Fix name

			name = store['name'].strip().replace("  "," ").replace("  "," ")
			name = name.replace("Truckdiesel","Truck Diesel").replace("TruckDiesel","Truck Diesel")

			if name == name.upper():
				name = name.title()

			split_name = name.split()
			for word in transform:
				if word[0] in split_name:
					name = name.replace(word[0], word[1])

			branch = name.replace(store['brand'],"").replace("Automaatti","").replace("Automat","").replace("Truck Diesel","")
			branch = branch.replace("CRT","").replace("Express","").replace("TS","").replace("STD","").lstrip()

			print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['location']['lat'], store['location']['lon']))

			make_osm_line("amenity", "fuel")
			make_osm_line("ref:st1", str(store['id']))
			make_osm_line("name", name)
			make_osm_line("brand", store['brand'])
			make_osm_line("branch", branch)
			
			make_osm_line("ADDRESS", store['fullAddress'])

			if name.find("Asko") >= 0:
				make_osm_line("access", "private")

			# Get station type

			station_country = None

			for station_type in store['stationTypes']:
				if station_type.find("automat") >= 0:
					make_osm_line("automated", "yes")
				elif station_type.find("truck") >= 0:
					make_osm_line("hgv", "yes")
				elif station_type.find("boat") >= 0:
					make_osm_line("boat", "yes")

				get_country (station_type)

			# Get all fuel types

			fuel_tags = {}

			for fuel_available in store['fuels']:

				get_country (fuel_available)

				for fuel_test in fuels:
					if fuel_available.find(fuel_test[0]) >= 0:
						if not(fuel_test[1] in fuel_tags):
							fuel_tags[fuel_test[1]] = True
						break

			for truck_available in store['trucks']:

				get_country (truck_available)

				for fuel_test in fuels:
					if truck_available.find(fuel_test[0]) >= 0:
						if not(fuel_test[1] in fuel_tags):
							fuel_tags[fuel_test[1]] = True
						break

			for fuel in fuel_tags:
				make_osm_line ("fuel:" + fuel, "yes")

			# Get services

			service_tags = {}

			for service_available in store['services']:

				get_country (service_available)

				for service_test in services:
					if service_available.find(service_test[0]) >= 0:
						if not(service_test[1] in service_tags):
							service_tags[service_test[1]] = True
						break

			for service in service_tags:
				make_osm_line(service, "yes")

			# Tag country after lookups (guess Sweden if empty)
			# Find county from looking up postal code translation, first two digits

			if station_country:
				make_osm_line("COUNTRY", station_country.title())
				if station_country == "norway":
					if municipality_id[int(store['postcode'])]:
						make_osm_line("COUNTY", county_names[ municipality_id[ int(store['postcode']) ][0:2] ])
			else:
				make_osm_line("COUNTRY", "Sweden")

			# Contact tags

			if 'email' in store:
				if store['email']:
					make_osm_line("email", store['email'])

			if 'telephone' in store:
				if store['telephone']:
					if station_country:
						make_osm_line("phone", countries[station_country] + " " + store['telephone'])
					else:
						make_osm_line("phone", store['telephone'])

			# Opening hours
			# Make array of opening hours per day

			hours = ["", "", "", "", "", "", ""]

			for day in store['storeOpeningHours']:
				if day['opens'] and day['closes']:
					struct_date = datetime.strptime(day['date'], "%Y-%m-%d")
					index = struct_date.weekday()
					hours[index] = day['opens'][0:5] + "-" + day['closes'][0:5]

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

			# For debugging/inspection

			if debug:
				make_osm_line("ZIP", store['postcode'])
				make_osm_line("STATION_TYPE", str(store['stationTypes']))
				make_osm_line("FUEL", str(store['fuels']))
				make_osm_line("TRUCKS", str(store['trucks']))
				make_osm_line("SERVICES", str(store['services']))

			# Done with OSM store node

			print('  </node>')


	# Produce OSM file footer

	print('</osm>')