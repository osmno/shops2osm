#!/usr/bin/env python
# -*- coding: utf8

# boots2osm
# Converts Boots pharmacies from Boots webpage to osm format for import/update
# Usage: boots2osm [input_filename.json] > output_filename.osm
# Default input file name are "boots.json" (copied from the html page)


import json
import cgi
import sys
import urllib2
from bs4 import BeautifulSoup


version = "0.1.0"


transform = [
	('Torg', 'torg'),
	('(Haugesund)', ''),
	('LadeTorget', 'Ladetorget'),
	('Helsepark', 'helsepark'),
	(', Oslo', ''),
	('Storsenter', 'storsenter'),
	('Senter', 'senter'),
	('Bruk', 'bruk'),
	('Helsehus', 'helsehus'),
	('Legevakt', 'legevakt'),
	(', Alta', ''),
	(', Haugesund', ''),
	(', Stavanger', ''),
	('Apotek', 'apotek')
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

	filename = ""

	if len(sys.argv) > 1:
		filename = sys.argv[1]

		with open(filename) as f:
			store_data = json.load(f)
			f.close()

	else:
		url = 'https://zpin.it/on/location/map/boots/ajax/search.php?c[z:cat:ALL]=1&lang=no&mo=440558&mn=default&json'
		header = {
			"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
			"X-Requested-With": "XMLHttpRequest"
			}

		request = urllib2.Request(url, headers=header)
		file = urllib2.urlopen(request)
		store_data = json.load(file)
		file.close()


	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="boots2osm v%s" upload="false">' % version)

	node_id = -10000

	# Loop through all stores and produce OSM tags

	for store in store_data['relations']['440558']:

		if store['pin']['name'] != "#N/A":

			node_id -= 1

			print('  <node id="%i" lat="%f" lon="%f">' % (node_id, store['pin']['latlng']['lat'], store['pin']['latlng']['lng']))

			# Fix name

			name = store['pin']['name']

			for word in transform:
				name = name.replace(word[0], word[1])
			name = name.replace("apotek ", "").replace(",", "").replace("  "," ").rstrip()

			branch = name.replace("Boots ", "")

			# Produce station tags

			make_osm_line("amenity", "pharmacy")
			make_osm_line("ref:boots", store['customId'])
			make_osm_line("name", name)
			make_osm_line("branch", branch)
			make_osm_line("brand", "Boots")

			make_osm_line("ID", str(store['pin']['id']))

			# Fetch information per store to get contact information and opening hours

			if not(filename):

				url = 'https://zpin.it/on/location/map/boots/ajax/company.php?id=%i&lang=no&mo=440558&mn=default&path=' % store['pin']['id']
				request = urllib2.Request(url, headers=header)
				page = urllib2.urlopen(request)
				storesoup = BeautifulSoup(page, features="html.parser")
				page.close()

				address = storesoup.find(class_="Zaddress").get_text()
				make_osm_line ("ADDRESS", address.replace("\nGatevisning", "").strip())

				contact = storesoup.find(class_="curved2")
				phone = contact.find("a").get_text()
				make_osm_line ("phone", "+47 " + phone.strip())

				email = contact.find("a").findNext("a")['href']
				email = email.replace("mailto:", "")
				make_osm_line ("email", email)

				# Build list for opening hours

				hours = ["", "", "", "", "", "", ""]
				table = storesoup.find(class_="openingHours").find("tbody").find_all("tr")

				for row in table:

					day_type = row.find("th").get_text()
					day_hours = row.find("td").get_text()

					if day_type == "Hverdag":
						hours[0] = day_hours
						hours[1] = day_hours
						hours[2] = day_hours
						hours[3] = day_hours
						hours[4] = day_hours
					elif (day_type == u"Lørdag") and (day_hours != "Stengt"):
						hours[5] = day_hours
					elif (day_type == u"Søndag") and (day_hours != "Stengt"):
						hours[6] = day_hours

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

				make_osm_line ("opening_hours", opening_hours)

			# Done with OSM store node

			print('  </node>')


	# Produce OSM file footer

	print('</osm>')