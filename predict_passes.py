#!/usr/bin/env python 
# -*- coding: utf-8 -*-

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
out_dir = app_config['out_dir']

# end of config 

time_range_end = time_range_start + datetime.timedelta(seconds=3600*24)

print "Time range: (%s,%s)" % (time_range_start.strftime('%Y%m%d_%H%M%S'),time_range_end.strftime('%Y%m%d_%H%M%S'))

passes_predict_file = "%s/%s-%s-avhrr-passes.yaml" % (out_dir ,time_range_start.strftime('%Y%m%d_%H%M%S'), aoi_name)

if os.path.isfile(passes_predict_file): #cache predictions in file
	print "passes already predicted in %s Abording!" % passes_predict_file
	exit()

tle_cache_file = "%s/%s-cache.tle" % (out_dir, time_range_start.strftime('%Y%m%d'))

if not os.path.isfile(tle_cache_file): #cache tle in file
	print "Downloading TLE"
	tle = get_tle_spacetrack(time_range_end, ",".join(app_config['platforms_ids']), app_config['spacetrack_login'], app_config['spacetrack_password'])
	with open(tle_cache_file, 'w') as ftle:
		ftle.write(tle)
		ftle.close

tles = {} #tle by platform
aoi_predicted_passes = {} # passes by platform

# pass prediction 
for platform in platforms:
	print "Platform %s" % platform 

	# select most siutable tle for platform and time
	tle = read_tle_from_file_db(platform, tle_cache_file, time_range_start)
	if tle == None:
		print "no siutable tle found for %s platform" % platform
		aoi_predicted_passes[platform] = []
	else:
		# save-selected TLE
		tles[platform] = tle
		# generate passes
		aoi_predicted_passes[platform] = generate_avhrr_platform_passes_over_aoi(tle, aoi_polygon, aoi_polygon_proj_string, time_range_start, time_range_end, 7000)

# write tles
tle_file = "%s/%s-avhrr.tle" % (out_dir,time_range_start.strftime('%Y%m%d_%H%M%S'))

with open(tle_file, 'w') as ftle:
	for platform in tles.keys():
		ftle.write(tles[platform].platform)
		ftle.write('\n')
		ftle.write(tles[platform].line1)
		ftle.write('\n')
		ftle.write(tles[platform].line2)
		ftle.write('\n')
		ftle.close

#write predicted passes
yaml.dump(aoi_predicted_passes, file(passes_predict_file, 'w')) 

# write slots shp (optional - debug or else)
shp_file = "%s/%s-%s-avhrr-passes.shp" % (out_dir , time_range_start.strftime('%Y%m%d_%H%M%S') , aoi_name)
save_passes_as_shp( shp_file, 
	aoi_polygon, aoi_polygon_proj_string, aoi_predicted_passes, tles)

print "Prediction done"
