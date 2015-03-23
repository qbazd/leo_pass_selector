#!/usr/bin/env python 
# -*- coding: utf-8 -*-

#example AVHRR file selector

import logging
logging.basicConfig()
#logging.debug("-- log message: ")

from granule_utils import generate_avhrr_platform_passes_over_aoi, get_pass_for_granule,save_passes_as_shp, read_tle_from_file_db, get_tle_spacetrack

import numpy as np
import datetime
from shapely.geometry import Polygon
import os.path

#load config
import yaml
app_config = yaml.load(file('predict_passes_config.yaml', 'r')) 

import argparse
parser = argparse.ArgumentParser(description='Predict passes for one day')

parser.add_argument('--day', action="store")

opts = parser.parse_args()
import datetime

time_range_start = datetime.datetime.strptime(opts.day, '%Y-%m-%d')

# eventualy read aoi_polygon from shapefile  
aoi_polygon_proj_string = "+proj=laea +lat_0=52 +lon_0=20  +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs"
aoi_polygon = Polygon( ((3628000.000, 4776000.000),(3628000.000, 3368000.000),(4908000.000, 3368000.000),(4908000.000, 4776000.000)) )
aoi_name = 'sb'

platforms = app_config['platforms']

# end of config 

time_range_end = time_range_start + datetime.timedelta(seconds=3600*24)

print "Time range: (%s,%s)" % (time_range_start.strftime('%Y%m%d_%H%M%S'),time_range_end.strftime('%Y%m%d_%H%M%S'))

passes_predict_file = "%s-%s-avhrr-passes.yaml" % (time_range_start.strftime('%Y%m%d_%H%M%S'), aoi_name)

if os.path.isfile(passes_predict_file): #cache predictions in file
	print "passes already predicted in %s Abording!" % passes_predict_file
	exit()

# read aoi_passes_timeslots from file
import yaml
aoi_predicted_passes = yaml.load(file(platform_passes_predict_file, 'r')) 

for platform in aoi_predicted_passes.keys():
	aoi_timeslots = aoi_predicted_passes[platform]
	print aoi_timeslots
print "Selected passes:"

# filter aoi_slots
aoi_timeslots_tmp = aoi_timeslots
aoi_timeslots = []
for slot in aoi_timeslots_tmp:
	if slot['aoi_cover'] > 99.0 :
		print "%s,%s,%5.1f%%" % (slot['time_slot'].strftime('%Y-%m-%d %H:%M:%S'),slot['slots'], slot['aoi_cover'])
		aoi_timeslots.append(slot)

print "Selected files for passes:"

# match received files to passes
import re
fp = open('AVHR.list')

for l0 in fp:
	match = None
	if platform == 'METOP-A':
		match = re.match(r'.*/AVHR_HRP_00_M02_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*', l0.strip())
	elif platform == 'METOP-B':
		match = re.match(r'.*/AVHR_HRP_00_M01_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*', l0.strip())

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
