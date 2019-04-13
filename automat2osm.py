#!/usr/bin/env python
# -*- coding: utf8

# automat2osm v0.1.0
# Converts Automat1 fuel stations from Automat1 html page "https://www.automat1.no/bensinstasjon/" to osm format for import/update
# Usage: python automat2osm.py > output_filename.osm


import urllib2
from bs4 import BeautifulSoup
import cgi
import json


# Produce a tag for OSM file

def make_osm_line(key,value):
    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		print ('    <tag k="%s" v="%s" />' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	# Load HTML page with shop data

	link = "https://www.automat1.no/bensinstasjon/"
	page = urllib2.urlopen(link)

	datasoup = BeautifulSoup(page, features="html.parser")

	# Produce OSM file header

	print ('<?xml version="1.0" encoding="UTF-8"?>')
	print ('<osm version="0.6" generator="automat2osm v0.1.0" upload="false">')

	node_id = -1000

	# Loop all stores and produce OSM file. Stores are grouped by county in html

	counties = datasoup.find(class_="dept-loop").find_all("script")

	for county in counties:

		county_string = county.get_text()
		start = county_string.find("[[")
		county_string = county_string[start:-4] + "]"
		stores = json.loads(county_string)

		for store in stores:

			node_id -= 1

			print('  <node id="%i" lat="%s" lon="%s">' % (node_id, store[0], store[1]))

			make_osm_line("amenity", "fuel")
			make_osm_line ("name", store[2])
			make_osm_line ("brand", "Automat1")
			make_osm_line ("branch", store[2].replace("Automat1 ", ""))

			make_osm_line ("ADDRESS", store[3])

			print('  </node>')


	# Produce OSM file footer

	print('</osm>')