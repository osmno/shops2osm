#!/usr/bin/env python
# -*- coding: utf8

# narvesen2osm
# Converts Narvesen stores from Narvesen html page "https://narvesen.no/finn-butikk" to osm format for import/update
# Usage: python narvesen2osm.py > output_filename.osm
# Reading postal codes and municipality codes from Posten, and county names from Kartverket


import cgi
import csv
import json
import urllib2
from bs4 import BeautifulSoup


version = "0.2.0"

transform = [
	('Jernbanet.', 'Jernbanetorget'),
	('T-bane', 't-bane'),
	('Storsenter', 'storsenter'),
	('Johansgt.', 'Johans gate'),
	('Rosenkr.', 'Rosenkrantz'),
	('Lufthavn', 'lufthavn'),
	('jbst.', 'jernbanestasjon'),
	('Tr. heim', 'Trondheim'),
	(u'Kjøpesenter', u'kjøpesenter'),
	('Stormarked', 'stormarked'),
	('Sentralstasjon', 'sentralstasjon'),
	('Fyllingsd.', 'Fyllingsdalen'),
	('Porsgr.', 'Porsgrunn'),
	('R. Amundsensgt.', 'Roald Amundsens gate'),
	('Park', 'park'),
	('Rutebilst.', 'rutebilstasjon'),
	('Kino', 'kino'),
	('Vest', 'vest'),
	('CC-vest', 'CC Vest'),
	('CC-Martn', 'CC Martn'),
	('Sentralsykeh.', 'Sentralsykehuset'),
	('kj. senter', u'kjøpesenter'),
	('Plan', 'plan'),
	('Hammersb.', 'Hammersborgs'),
	('Storgt.', 'Storgata'),
	('Kongsb.', 'Kongsberg'),
	('Strandgt.', 'Strandgata'),
	('Stors.', 'storsenter'),
	('Storsent.', 'Storsenter'),
	('storsent.', 'storsenter'),
	('Stort.', 'Stortorvet'),
	('Brygge', 'brygge'),
	('Universitetssykehus', 'universitetssykehus'),
	(u'Søbstadvn.', u'Søbstadveien'),
	('Studentboliger', 'studentboliger'),
	(u'Lørensk.', u'Lørenskog'),
	('Bussterminal', 'bussterminal'),
	('Sykehus', 'sykehus'),
	('Univ. sykeh.', 'Universitetssykehuset'),
	('Borggt.', 'Borggata'),
	(u'Sør', u'sør'),
	('Dronningensgt.', 'Dronningens gate'),
	('Eitrheimsvn.', 'Eitrheimsvegen'),
	('Jernbanegt', 'Jernbanegata'),
	('Avgang', 'avgang'),
	('Senter', 'senter'),
	('Fr. Stangsgt.', 'Fredrik Stangs gate'),
	('Utland', 'utland'),
	('Gravdalsgt.', 'Gravdalsgata'),
	('Havneggt.', 'Havnegata'),
	('Fylkessykeh.', 'Fylkessykehuset'),
	('Torg', 'torg'),
	('gt.', 'gate'),
	('gt', 'gate')
]


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

	postal_file = urllib2.urlopen('https://www.bring.no/postnummerregister-ansi.txt')
	postal_codes = csv.DictReader(postal_file, fieldnames=['zip','post_city','municipality_ref','municipality','type'], delimiter="\t")
	zip_table = list(dict())
	for row in postal_codes:
		entry = {
			'post_name': row['post_city'].decode('iso-8859-1'),
			'municipality_ref': row['municipality_ref'],
			'municipality_name': row['municipality'].decode('iso-8859-1')
		}
		zip_table.append(entry)
	postal_file.close()

	# Load HTML page with shop data

	link = "https://narvesen.no/finn-butikk"
	page = urllib2.urlopen(link)

	datasoup = BeautifulSoup(page, features="html.parser")

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="narvesen2osm v%s" upload="false">' % version)

	node_id = -11000

	# Loop all stores and produce OSM file

	stores = datasoup.find(id="Maps-475-list").find_all("li")

	for store in stores:

#		sys.stderr.write(str(store))

		node_id -= 1

		print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store['data-lat'], store['data-lng']))

		branch = store['data-title'].replace(".", ". ").replace(",", ", ")
		for word in transform:
			branch = branch.replace(word[0], word[1])
		branch = branch[0].upper() + branch[1:].replace("  ", " ").replace(" ,", ",").replace(" /", "/").strip()

		make_osm_line("shop", "kiosk")
		make_osm_line ("ref:narvesen", store['data-externalid'])
		make_osm_line ("name", "Narvesen")
		make_osm_line ("brand", "Narvesen")
		make_osm_line ("branch", branch)

		# Fetch address

		addrsoup = store.find(class_="adr")
		street = addrsoup.find(class_="street-address").get_text()
		city = addrsoup.find(class_="postal").find(class_="locality").get_text()

		make_osm_line ("ADDRESS", street + ", " + city)

		# Find county from looking up postal code translation, first two digits

		county = ""
		for zip_code in zip_table:
			if (zip_code['post_name'] == city) or (zip_code['municipality_name'] == city):
				county = county_names[ zip_code['municipality_ref'][0:2] ]
				break

		if not(county):
			if city == "STAVANGER LUFTHAVN":
				county = "Rogaland"
			elif city == "NORDBYHAGEN":
				county = "Akershus"

		if county:
			make_osm_line("COUNTY", county)

		# Done with OSM store node

		print('  </node>')


	# Produce OSM file footer

	print('</osm>')