#!/usr/bin/env python
# -*- coding: utf8

# bunnpris2osm
# Converts Bunnpris stores from Bunnpris html page "https://bunnpris.no/butikker" to osm format for import/update
# Usage: python bunnpris2osm.py > output_filename.osm
# Loads postal codes and municipality codes from Posten/Bring and county names from Kartverket/Geonorge


import urllib2
from bs4 import BeautifulSoup
from datetime import datetime
import json
import cgi
import csv
import re


version = "0.2.0"

transform = [
	('Brygge', 'brygge'),
	(u'Allè', u'allé'),
	('Basar', 'basar'),
	('Plass', 'plass'),
	('Konowsgate', 'Konows gate'),
	('Sentrum Molde', 'Molde sentrum'),
	('Meyersgt', 'Meyers gate'),
	('Welhavensgate', 'Welhavens gate')
]

services = {
	'Catering': 'catering',
	'Gourmet': '',
	'HjemLevering': 'delivery',
	'Medisinutsalg': 'pharmacy',
	'Posten': 'posten',
	'Postnord': 'postnord',
	'Rikstoto': 'rikstoto',
	'Selvbetjent': '',
	'Sondagsaapent': '',
	'Tipping': 'tipping'
}

days = ('Mandag','Tirsdag','Onsdag','Torsdag','Fredag',u'Lørdag',u'Søndag')

short_days = ('Mo','Tu','We','Th','Fr','Sa','Su')


# Produce a tag for OSM file

def make_osm_line(key,value):

    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


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

	link = "https://bunnpris.no/butikker"
	request = urllib2.Request(link, headers=header)
	page = urllib2.urlopen(request)

	soup = BeautifulSoup(page, features="html.parser")

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="bunnpris2osm v%s" upload="false">' % version)

	node_id = -11000

	# Loop all stores and produce OSM file

	stores = soup.find_all(class_="mapMarker")

	for store in stores:

		node_id -= 1

		print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['data-poslat'], store['data-poslng']))

		name = store['data-name'].strip()
		for word in transform:
			name = name.replace(word[0], word[1])

		branch = name.replace("Bunnpris ","").replace("& Gourmet ","")

		make_osm_line("shop", "supermarket")
		make_osm_line ("ref:bunnpris", store['data-id'])
		make_osm_line ("name", name)
		make_osm_line ("brand", "Bunnpris")
		make_osm_line ("branch", branch)

		# Fetch store information (json format)

		json_data = json.loads(store['data-dataobject'])
		datasoup = BeautifulSoup (json_data['Info'], features="html.parser")

		rightside = datasoup.find(class_="clearfix").find(class_="rightside")
		leftside = datasoup.find(class_="clearfix").find(class_="leftside")

		# Produce address line

		address = rightside.stripped_strings
		address_line = address.next()
		part = address.next()
		if part != "Tlf:" and part != "E-post:" and part != u"Kjøpmann:":
			address_line = address_line + ", " + part
		if not("," in address_line):
			address_line = branch + ", " + address_line
		make_osm_line ("ADDRESS", address_line)
		
		# Produce contact details

		phonesoup = rightside.find(itemprop="telephone")
		if phonesoup:
			make_osm_line ("phone", "+47 " + phonesoup['href'].replace("tel:","").replace("mobil:",";+47 ").replace("-",";+47 ").replace("/",";+47 "))

		emailsoup = rightside.find(itemprop="email")
		if emailsoup:
			make_osm_line ("email", emailsoup['href'].replace("mailto:","").lower())

		# Produce services

		for service in leftside.find(class_="services").find_all("span"):
			if service['title'] in services:
				if services[service['title']] != "":
					make_osm_line ("service:"+ services[service['title']], "yes")
			else:
				make_osm_line ("service:"+ service['title'], "yes")

		# Opening hours
		# Make array of opening hours per day
		# Input format: "Mandag - Fredag" "09  - 20"
		# Ignore public holidays etc.

		hours = ["", "", "", "", "", "", ""]

		for day in leftside.find("table").find_all("tr"):

			day_name = day.find("td").get_text().replace(" - ","-")
			day_hours = day.find(class_="time").get_text().replace(" - ","-")

			if not(day_hours == "stengt"):

				hours_split = day_hours.split("-")
				if not(":" in hours_split[0]):
					hours_split[0] = hours_split[0] + ":00"
				if not(":" in hours_split[1]):				
					hours_split[1] = hours_split[1] + ":00"
				if hours_split[1] == "00:00":
					hours_split[1] = "24:00"
				day_hours = "-".join(hours_split)

#				time_start = datetime.strftime(datetime.strptime(hours_split[0],"%H:%M"), "%H:%M")
#				time_end = datetime.strftime(datetime.strptime(hours_split[1],"%H:%M"), "%H:%M")
#				day_hours = time_start + "-" + time_end

				day_split = day_name.split("-")
				if day_split[0] in days:
					if len(day_split) == 1:
						hours[days.index(day_name)] = day_hours
					else:
						for i in range(days.index(day_split[0]), days.index(day_split[1]) + 1):
							hours[i] = day_hours

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

		reg = re.search(r', ([0-9][0-9][0-9][0-9]) ', address_line, flags=re.UNICODE)
		if reg:
			postal_code = int(reg.group(1))
			if municipality_id[postal_code]:
				make_osm_line("COUNTY", county_names[ municipality_id[postal_code][0:2] ])
			elif postal_code == 7330:
				make_osm_line("COUNTY", u"Trøndelag")


		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')