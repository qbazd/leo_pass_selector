#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import logging
logging.basicConfig()
#logging.debug("-- log message: ")

from granule_utils import generate_avhrr_platform_passes_over_aoi, get_pass_for_granule,save_passes_as_shp, read_tle_from_file_db, get_tle_spacetrack

#import urllib
#import os
#import glob
import numpy as np
import datetime
from shapely.geometry import Polygon

#load credentials
import yaml
spacetrack = yaml.load(file('spacetrack.yaml', 'r')) 

# eventualy read aoi_polygon from shapefile  
aoi_polygon_proj_string = "+proj=laea +lat_0=52 +lon_0=20  +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs"
aoi_polygon = Polygon( ((3628000.000, 4776000.000),(3628000.000, 3368000.000),(4908000.000, 3368000.000),(4908000.000, 4776000.000)) )
aoi_name = 'sb'

platform = 'METOP-A'

# "METOP-A", "METOP-B", "NOAA 19"
#aoi_area = aoi_polygon.area / 1000000 # m^2 -> km^2
#print "%s area: %.0f" % (aoi_name , aoi_area)

time_range_start = datetime.datetime(2012, 07, 26, 00, 00, 0)
time_range_start = datetime.datetime(2015, 01, 26, 00, 00, 0)
time_range_end = time_range_start + datetime.timedelta(seconds=3600*24)

# end of config 

print "Platform %s" % platform 
print "time range: (%s,%s)" % (time_range_start.strftime('%Y%m%d%H%M%S'),time_range_end.strftime('%Y%m%d%H%M%S'))

# choose a platform
platform_passes_predict_file = "%s-%s-%s-passes.yaml" % (time_range_start.strftime('%Y%m%d%H%M%S'), platform, aoi_name)

tle_file = "%s-cache.tle" % time_range_start.strftime('%Y%m%d')

import os.path

if not os.path.isfile(tle_file): #cache tle in file
	tle = get_tle_spacetrack(time_range_end, spacetrack['login'], spacetrack['password'])
	with open(tle_file, 'w') as ftle:
		ftle.write(tle)
		ftle.close

# select most siutable tle for platform and time
tle = read_tle_from_file_db(platform, tle_file, time_range_start)
if tle == None:
	print "no siutable tle found"
	exit()
#print tle

# pass prediction 
if not os.path.isfile(platform_passes_predict_file): #cache predictions in file
	# generate passes
	aoi_timeslots = generate_avhrr_platform_passes_over_aoi(platform, aoi_polygon, aoi_polygon_proj_string, time_range_start, time_range_end, 7000 ,tle )
	#print aoi_timeslots
	# eventualy write to csv file
	import yaml
 	yaml.dump(aoi_timeslots, file(platform_passes_predict_file, 'w')) 

	# save slots shp (optional - debug or else)
	save_passes_as_shp(time_range_start.strftime('%Y%m%d%H%M%S') + ("-%s-%s.shp" % (platform, aoi_name)), 
		platform, aoi_polygon, aoi_polygon_proj_string, aoi_timeslots, tle)

	aoi_timeslots = None

# read aoi_passes_timeslots from file
import yaml
aoi_timeslots = yaml.load(file(platform_passes_predict_file, 'r')) 

print "Selected passes:"

# filter aoi_slots
aoi_timeslots_tmp = aoi_timeslots
aoi_timeslots = []
for slot in aoi_timeslots_tmp:
	if slot['aoi_cover'] > 50.0 :
		print "%s,%s,%5.1f%%" % (slot['time_slot'].strftime('%Y-%m-%d %H:%M:%S'),slot['slots'], slot['aoi_cover'])
		aoi_timeslots.append(slot)

print "Selected files for passes:"

# match received files to passes
import re
fp = open('AVHR.list')

for l0 in fp:
	match = re.match(r'.*/AVHR_HRP_00_M02_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*', l0.strip())
	if match:
		time_slot = datetime.datetime(int(match.group(1)),int(match.group(2)),int(match.group(3)),int(match.group(4)),int(match.group(5)),int(match.group(6)))
		if time_slot > time_range_end or time_slot < time_range_start:
			continue
		slot_for_granule = get_pass_for_granule(time_slot, time_slot + datetime.timedelta(seconds=60), aoi_timeslots)
		if slot_for_granule != None:
			print "%s,%s,%s" % (slot_for_granule['time_slot'].strftime('%Y-%m-%d %H:%M:%S'),slot_for_granule['slots'],l0.strip())
		#else:
			#print "rm %s" % l0.strip()

fp.close()
