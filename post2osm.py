#!/usr/bin/env python
# -*- coding: utf8

# post2osm
# Converts post offices from Posten XML to osm format for import/update
# Usage: python post2osm.py
# Creats output file 'postkontor.osm'


import cgi
import HTMLParser
import sys
import urllib2
from xml.etree import ElementTree


version = "0.4.0"


transform_name = [
	('AS', ''),
	('As ', ''),
	('A/L', ''),
	('BYGG', 'Bygg'),
	('Sentrum', 'sentrum'),
	(u'- avd. Roan', ''),
	('Eftf', 'eftf'),
	('Handelslag', 'handelslag'),
	('Handelskompani', 'handelskompani'),
	('Service Senter', 'servicenter'),
	('Servicenter', 'servicenter'),
	('Bilsenter As', 'bilsenter'),
	('Storsenter', 'storsenter'),
	('Verk', 'verk'),
	('Maze', u'Máze'),
	(' - ', ', '),
	(' I ', ' i ')
]

chain_list = [
	('Best'),
	('Bilhjelp 1'),
	('Bring Express'),
	('Bunnpris & Gourmet'),
	('Bunnpris'),
	("Bygger'n"),
	('Circle K'),
	('Clas Ohlson'),
	('Coop Byggmix'),
	('Coop Jernvarer'),
	('Coop Marked'),
	('Coop Mega'),
	('Coop Obs! Hypermarked'),
	('Coop Obs!'),
	('Coop Prix'),
	('Coop'),
	(u'Elkjøp Megastore'),
	(u'Elkjøp'),
	('Europris'),
	('Eurospar'),
	('Extra'),
	('Hageland'),
	(u'Helgø Meny'),
	('Jernia'),
	('Joker'),
	('Kiwi Minipris'),
	('Kiwi'),
	('Matkroken'),
	('Meny'),
	('Mix Handleriet'),
	('Mix'),
	(u'Nærbutikken'),
	('Oasen'),
	('Obs Bygg'),
	('Plantasjen'),
	('Prix'),
	('Rema 1000'),
	('Shell 7-Eleven'),
	('Shell/7-Eleven'),
	('Skoringen'),
	('Spar'),
	('Tilbords'),
	('YX') ]


# Produce a tag for OSM file

def make_osm_line(key,value):
    if value != "":
		parser = HTMLParser.HTMLParser()
		value = parser.unescape(value)
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		file.write ('    <tag k="%s" v="%s" />\n' % (key, encoded_value))


# Return opening hours in osm format
# Input from Bring API: "Man - Fre: 0800-2200, Lør: 0800-2000"
# Input from Posten web: "Man.–fre. 08.00–22.00","Lør. 08.00–20.00"

def opening_hours(hours):

	day_conversion = {
		'man': 'Mo',
		'tir': 'Tu',
		'ons': 'We',
		'tor': 'Th',
		'fre': 'Fr',
		u'lør': 'Sa',
		u'søn': 'Su'}

	if hours != None:

		result = hours.lower()
		result = result.replace(u"–","-")
		result = result.replace(".-","-")
		result = result.replace(". "," ")
		result = result.replace(" - ","-")
		result = result.replace(":","")

		for day_in, day_out in day_conversion.items():
			result = result.replace(day_in, day_out)

		result = result.replace(".",":")
		result = result.replace("00:01","00:00")
		result = result.replace("23:58","24:00")
		result = result.replace("23:59","24:00")

		if result == "Mo-Su 00:00-24:00":
			result = "24/7"

		return result

	else:
		return ""


# Main program

if __name__ == '__main__':

	# Read all data into memory

	url = "http://public.snws.posten.no//SalgsnettServicePublic.asmx/GetEnheter?searchValue=&landkode=NO"
	file = urllib2.urlopen(url)
	tree = ElementTree.parse(file)
	file.close()

	ns = {'ns0': 'https://public.snws.posten.no/SalgsnettService.asmx/'}  # Namespace

	root = tree.getroot()

	# Produce OSM file header

	file = open("postkontor.osm", "w")

	file.write ('<?xml version="1.0" encoding="UTF-8"?>\n')
	file.write ('<osm version="0.6" generator="post2osm v%s">\n' % version)

	node_id = -1000

	# Iterate all post offices and produce OSM tags

	for office in root.iterfind('ns0:EnhetDTO', ns):

		if (office.find('ns0:PostnrBesoksadresse/ns0:Land/ns0:Kode', ns) != None) and \
			(office.find('ns0:PostnrBesoksadresse/ns0:Land/ns0:Kode', ns).text == "NO") and \
			(office.find('ns0:Status/ns0:Navn', ns).text == "Aktiv") and \
			(office.find('ns0:EnhetsType/ns0:EnhetsType', ns).text not in ["27", "36"]):  # Avoid automats

			node_id -= 1

			latitude = office.find('ns0:Latitude', ns).text
			longitude = office.find('ns0:Longitude', ns).text
			if (latitude[0] == "-") or (longitude[0] == "-"):
				latitude = "0"
				longitude = "0"

			file.write ('  <node id="%i" lat="%s" lon="%s">\n' % (node_id, latitude, longitude))

			make_osm_line ("amenity", "post_office")
			make_osm_line ("ref:posten", office.find('ns0:Enhetsnr', ns).text)
#			make_osm_line ("posten:id", office.find('ns0:IDEnhet', ns).text)
			make_osm_line ("brand", "Posten")

			# Get address

			address = office.find('ns0:PostnrBesoksadresse', ns)

			if office.find('ns0:Besoksadresse', ns).text != None:
				address_line = office.find('ns0:Besoksadresse', ns).text.strip() + ", "
			else:
				address_line = ""
			address_line += address.find('ns0:Postnr', ns).text.strip() + " " + address.find('ns0:Poststed', ns).text

			make_osm_line ("ADDRESS", address_line)
			make_osm_line ("MUNICIPALITY", address.find('ns0:Kommune', ns).text)
			make_osm_line ("COUNTY", address.find('ns0:Fylke', ns).text)

			# Adjust name and operator according to type of post office

			office_type = office.find('ns0:EnhetsType/ns0:EnhetsType', ns).text
			name = office.find('ns0:EnhetsNavn', ns).text
			operator = office.find('ns0:Navn', ns).text

			for word_from, word_to in transform_name:
				name = name.replace(word_from, word_to)
				operator = operator.replace(word_from, word_to)

			if operator.find("Kiwi") >= 0:
				for number in ['0','1','2','3','4','5','6','7','8','9']:
					operator = operator.replace(number, '')

			name = name.replace("  "," ").strip()
			operator = operator.replace("  "," ").strip()
			alt_name = ""

			if office_type == "4":  # Post i butikk
				name = name.replace("Post i Butikk", "post i butikk")
				alt_name = operator + " post i butikk"
				make_osm_line("post_office:type", "post_partner")

			elif office_type == "19":  # Pakkeutlevering
				name = name.replace("Posten ", "")
				alt_name = operator + " pakkeutlevering"
				make_osm_line("post_office:type", "parcel_delivery")

			elif office_type == "21":  # Postkontor
				operator = "Posten"

			elif office_type == "27":  # Pakkeautomat
				name = name.replace('Post i Butikk', 'post i butikk')
				operator = ""
				make_osm_line("post_office:type", "parcel_automat")

			elif office_type == "32":  # Postpunkt (egendrevet)
				operator = "Posten"

			elif office_type == "33":  # Postpunkt
				alt_name = operator + " postpunkt"

			elif office_type == "37":  # Pakkeboks
				make_osm_line("post_office:type", "parcel_automat")
				operator = "Posten"

			elif office_type == "1":  # Bedriftsenter
				operator = "Posten"
				make_osm_line("post_office:type", "business_centre")

			else:
				make_osm_line ("FIXME", "Ukjent enhetstype: '%s'" % office_type)
				sys.stderr.write("Ukjent enhetstype: '%s'\n" % office_type)

			make_osm_line ("name", name)

			if alt_name and (alt_name != name):
				make_osm_line ("alt_name", alt_name)

			# Produce osm tags for operator brand

			make_osm_line("operator", operator)

			for chain in chain_list:
				if operator.find(chain) >= 0:
					make_osm_line("OPERATOR_CHAIN", chain)
					break

			# Opening hours

			hours = office.find('ns0:Apningstider/ns0:ApningstidDTO/ns0:ApningstidCSV', ns).text
#			make_osm_line("HOURS", "%s" % hours)
			make_osm_line("opening_hours", opening_hours(hours))

			# Done with OSM office node

			file.write ('  </node>\n')


	# Produce OSM file footer

	file.write ('</osm>\n')
