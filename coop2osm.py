#!/usr/bin/env python
# -*- coding: utf8

# coop2osm
# Converts Coop stores from Coop API or JSON file to OSM format for import/update
# Usage: python coop2osm.py [input_filename.json] > output_filename.osm
# Loads data from Coop API unless input file  is given
# Loads postal codes from POsten/Bring and municipality codes from Kartverket/Geonorge


import json
import cgi
import sys
import csv
import re
import urllib2


version = "0.3.0"

brands = {
	'hyper': {'name': 'Obs', 'shop': 'supermarket'},
	'extra': {'name': 'Extra', 'shop': 'supermarket'},
	'mega': {'name': 'Coop Mega', 'shop': 'supermarket'},
	'prix': {'name': 'Coop Prix', 'shop': 'supermarket'},
	'matkroken': {'name': 'Matkroken', 'shop': 'supermarket'},
	'marked': {'name': 'Coop Marked', 'shop': 'supermarket'},
	'byggmix': {'name': 'Coop Byggmix', 'shop': 'doityourself'},
	'bygg': {'name': 'Obs Bygg', 'shop': 'doityourself'},
	'elektro': {'name': 'Coop Elektro', 'shop': 'electronics'}
}

transform = [
	('Brygge', 'brygge'),
	('Hus', 'hus'),
	('Torv', 'torv'),
	('Torg', 'torg'),
	('Park', 'park'),
	('Plass', 'plass'),
	('Gate', 'gate'),
	('Senter', 'senter'),
	('Sentrum', 'sentrum'),
	('Shopping', 'shopping'),
	('Handelslag', 'handelslag'),
	('Storsenter', 'storsenter'),
	(u'Allè', u'allé'),
	('Abc', 'ABC'),
	('Epa', 'EPA'),
	('Kiellandsg', 'Kiellands gate'),
	('Kiellandsp', 'Kiellands plass'),
	('Krsand', 'Kristiansand'),
	('Hausmannsgate', 'Hausmanns gate'),
	('St.Halvardsgt.', 'St. Halvards gate'),
	('Olavsgate', 'Olavs gate'),
	('Olavsvei', 'Olavs vei'),
	('Rogalandsgate', 'Rogalandsgata'),
	('Schweigaardsgate', 'Schweigaards gate'),
	('Theresesgate', 'Thereses gate'),
	('Thranesgate', 'Thranes gate'),
	('Klepp St', 'Klepp stasjon'),
	('Vossegt.', 'Vossegata'),
	('Vg-huset', 'VG-huset'),
	(u'Steen&Strøm', u'Steen & Strøm'),
	(' I ', ' i '),
	(' Og ', ' og ')
]

days = ('Mandag','Tirsdag','Onsdag','Torsdag','Fredag',u'Lørdag',u'Søndag')

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

		link = "https://coop.no/StoreService/StoresByBoundingBox?locationLat=59&locationLon=10&latNw=73&lonNw=0&latSe=56&lonSe=37&chainId=999"
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
	print ('<osm version="0.6" generator="coop2osm v%s" upload="false">' % version)

	node_id = -1000

	# Loop through all stores and produce OSM tags

	for store in store_data:

		node_id -= 1
		brand = brands[store['ChainClassName']]
		name = store['Name'].strip()

		for word in transform:
			name = name.replace(word[0], word[1])
		name = name[0].upper() + name[1:]

		print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['Lat'], store['Lng']))

		make_osm_line("shop", brand['shop'])

		make_osm_line("ref:coop", store['StoreId'])
		make_osm_line("name", brand['name'] + " " + name)
		make_osm_line("brand", brand['name'])
		make_osm_line("branch", name)

		if 'Email' in store:
			if store['Email']:
				make_osm_line("email", store['Email'])
		if 'Phone' in store:
			if store['Phone']:
				make_osm_line("phone", "+47 " + store['Phone'])
		
		make_osm_line("ADDRESS", store['Address'])


		# Extra services

		if 'InStoreServices' in store:
			for service in store['InStoreServices']:
				if service == 'tipping':
					make_osm_line('service:tipping', 'yes')
				elif service == 'post':
					make_osm_line('service:posten', 'yes')
				elif service =='postnord':
					make_osm_line('service:postnord', 'yes')
				elif service == 'toto':
					make_osm_line('service:rikstoto', 'yes')
				else:
					make_osm_line('service:' + service, 'yes')


		# Opening hours
		# Make array of opening hours per day

		hours = ["", "", "", "", "", "", ""]

		for day in store['OpeningHours']:
			if not(day['Closed']):
				hours[days.index(day['Weekday'])] = day['OpenString'].replace("-00:00", "-24:00")

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

		opening_hours = opening_hours.lstrip(", ")

		if len(opening_hours) == 17:
			if (opening_hours == "Mo-Su 00:00-24:00") or ((opening_hours[0:5] == "Mo-Su") and (opening_hours[6:11] == opening_hours[12:17])):
				opening_hours = "24/7"

		make_osm_line("opening_hours", opening_hours)

		# Find county from looking up postal code translation, first two digits

		reg = re.search(r', ([0-9][0-9][0-9][0-9]) ', store['Address'], flags=re.UNICODE)
		if reg:
			postal_code = int(reg.group(1))
			if municipality_id[postal_code]:
				make_osm_line("COUNTY", county_names[ municipality_id[postal_code][0:2] ])
			elif postal_code == 9000:
				make_osm_line("COUNTY", "Troms")
			elif (postal_code == 7976) or (postal_code == 7977):
				make_osm_line("COUNTY", u"Trøndelag")


		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')