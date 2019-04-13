#!/usr/bin/env python
# -*- coding: utf8

# norgesgr2osm
# Converts Norgesgruppen stores from Norgesgruppen API or JSON file to OSM format for import/update
# Usage: python norgesgr2osm.py [input_filename.json] > output_filename.osm
# Permitted input file names: meny, spar, kiwi, joker, narbutikken.json
# Loads store data from Norgesgruppen API


import json
import cgi
import sys
import urllib2


version = "0.3.0"


brands = {
	'meny': {'name': 'Meny', 'shop': 'supermarket', 'api': '1300'},
	'spar': {'name': 'Spar', 'shop': 'supermarket', 'api': '1210'},
	'kiwi': {'name': 'Kiwi', 'shop': 'supermarket', 'api': '1100'},
	'joker': {'name': 'Joker', 'shop': 'supermarket', 'api': '1220'},
	'narbutikken': {'name': u'Nærbutikken', 'shop': 'supermarket', 'api': '1270'}
}

transform = [
	('Brygge', 'brygge'),
	('Bruk', 'bruk'),
	(u'Gården', u'gården'),
	('Camping', 'camping'),
	('Hus', 'hus'),
	('Torv', 'torv'),
	('Torg', 'torg'),
	('Park', 'park'),
	('Plass', 'plass'),
	('Gate', 'gate'),
	('Verk', 'verk'),
	('Hageby', 'hageby'),
	('Kino', 'kino'),
	('Mat', 'mat'),
	('Mart`nSenteret', "Mart'nsenteret"),
	('Senter', 'senter'),
	('Senteret', 'senteret'),
	('Sentervei', 'sentervei'),
	('Sentrum', 'sentrum'),
	('Shopping', 'shopping'),
	('Handelslag', 'handelslag'),
	('Storsenter', 'storsenter'),
	('Fengsel', 'fengsel'),
	('Kolonial', 'kolonial'),
	('Handel', 'handel'),
	('Landhandel', 'landhandel'),
	('Dagligvare', 'dagligvare'),
	('Landsbyservice', 'landsbyservice'),
	('Bussterminal', 'bussterminal'),
	('Togstasjon', 'togstasjon'),
	('Stasjon', 'stasjon'),
	('Eftf.', 'eftf.'),
	(u'Allè', u'allé'),
	(u'Allé', u'allé'),
	('Gml Fr.stad', 'Gamle Fredrikstad'),
	('Langesgate', 'Langes gate'),
	('Thoresens Vei', 'Thoresens vei'),
	('Olav V`s', "Olav V's"),
	('Gml.Fredrikstad', 'Gamle Fredrikstad'),
	(u'Åfjord.', u'Åfjord'),
	('LILAND', 'Liland'),
	('JELSA', 'Jelsa'),
	(u'Åmdals-Verk', u'Åmdals verk'),
	('Bjelkesgate', 'Bjelkes gate'),
	('Allehelgensgate', 'Allehelgens gate'),
	('Fayesgate', 'Fayes gate'),
	('Kronprinsensgate', 'Kronprinsens gate'),
	('Theresesgate', 'Thereses gate'),
	(u'Bjørnsonsgate', u'Bjørnsons gate'),
	('Langesgate', 'Langes gate'),
	('Gudesgate', 'Gudes gate'),
	('Konowsgate', 'Konows gate'),
	('Juelsgate', 'Juels gate'),
	('Vogtsgate', 'Vogts gate'),
	('Thranesgate', 'Thranes gate'),
	('Skogvei', 'skogvei'),
	(u'Holset gården', u'Holsetgården'),
	('Olavsplass', 'Olavs plass'),
	('Torget Vest', 'Torget vest'),
	(u'Stoa Øst', u'Stoa øst'),
	(u'Ankertorget -Oslo', 'Ankertorget, Oslo'),
	(u' - ', ', '),
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

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="norgesgr2osm v%s" upload="false">' % version)

	node_id = -3000

	# Loop through all or selected brands

	for brand_key, brand in brands.iteritems():

		if brand_key + ".json" in sys.argv or len(sys.argv) == 1:

			# Read all data into memory

			if len(sys.argv) > 1:
				filename = sys.argv[1]
				with open(filename) as file:
					store_data = json.load(file)
					file.close()

			link = "https://platform-rest-prod.ngdata.no/api/FindStore/StoresClosestToMe/%s/?" % brand['api'] +\
					"latitude=65.4&longitude=16.8&minnumberofstores=1&maxNumberOfStores=0&maxDistance=2069637"
			header = {
				"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
				"X-Requested-With": "XMLHttpRequest"
				}

			request = urllib2.Request(link, headers=header)
			file = urllib2.urlopen(request)
			store_data = json.load(file)
			file.close()

			# Loop through all stores and produce OSM tags

			for store_item in store_data:

				store = store_item['store']

				node_id -= 1

				if "location" in store:
					latitude = store['location']['latitude']
					longitude = store['location']['longitude']
				else:
					latitude = 0.0
					longitude = 0.0

				print('  <node id="%i" lat="%f" lon="%f">' % (node_id, latitude, longitude))

				make_osm_line("shop", brand['shop'])
				make_osm_line("ref:norgesgruppen", str(int(store['id']) - 7080000000000))

				# Set brand and branch names for name tag

				split_name = store['name'].split(" ")

				if split_name[0] == u"Helgø":
					brand_name = u"Helgø Meny"
					branch_name = " ".join(split_name[2:])

				elif split_name[0] == u"Lerøy":
					brand_name = ""
					branch_name = u"Lerøy mat"

				else:
					brand_name = split_name[0].rstrip().title()  # Including Eurospar
					if split_name[1].isnumeric():                # Kiwi
						branch_name = " ".join(split_name[2:])
					else:
						branch_name = " ".join(split_name[1:])
					branch_name = branch_name.lstrip(" ")

				# Fix name

				for word in transform:
					branch_name = branch_name.replace(word[0], word[1])
				branch_name = branch_name[0].upper() + branch_name[1:].strip()

				if brand_name == "":
					store_name = branch_name
				else:
					store_name = brand_name + " " + branch_name


				make_osm_line("name", store_name)
				make_osm_line("brand", brand['name'])
				make_osm_line("branch", branch_name)

				if 'email' in store:
					if store['email']:
						make_osm_line("email", store['email'].strip())
				if 'phone' in store:
					if store['phone'] and store['phone'] != "0":
						make_osm_line("phone", "+47 " + store['phone'].strip())

				address = ""
				if 'visitaddress' in store:
					if store['visitaddress']:
						address = store['visitaddress'] + ", "

				address = address + store['zipcode'] + " " + store['zipcitycode']
				
				make_osm_line("ADDRESS", address)
				make_osm_line("COUNTY", store['county'])

				# Extra services

				if store['services'] != "":
					for service in store['services'].split(", "):
						if service == 'TIPPING':
							make_osm_line('service:tipping', 'yes')
						elif service == 'PIB':
							make_osm_line('service:posten', 'yes')
						elif service == 'RIKSTOTO':
							make_osm_line('service:rikstoto', 'yes')
						elif service == 'BIB Full':
							make_osm_line('service:bank', 'yes')
						elif service != "TRUMFBONUS":
							make_osm_line('service:' + service.lower(), 'yes')

				# Opening hours
				# Make array of opening hours per day

				hours = ["", "", "", "", "", "", ""]

				for day in store['openinghours']['days']:
					if day['label'] == "Hverdager":
						if day['from'] != "":
							hours[0] = day['from'] + "-" + day['to']
							hours[1] = day['from'] + "-" + day['to']
							hours[2] = day['from'] + "-" + day['to']
							hours[3] = day['from'] + "-" + day['to']
							hours[4] = day['from'] + "-" + day['to']
					elif day['label'] in days:
						if  day['from'] != "":
							hours[days.index(day['label'])] = day['from'] + "-" + day['to']
					else:
						raise KeyError('Unknown day "%s"' % day['label'])

				for i in range(7):
					hours[i] = hours[i].replace("00:01","00:00").replace("23:59","24:00").replace("-00:00","-24:00")

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

				# Done with OSM store node

				print('  </node>')


	# Produce OSM file footer

	print('</osm>')