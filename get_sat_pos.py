#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import logging
logging.basicConfig()
#logging.debug("-- log message: ")

from granule_utils import generate_avhrr_platform_passes_over_aoi, get_pass_for_granule,save_passes_as_shp, read_tle_from_file_db, get_tle_spacetrack, get_avhrr_nadir_ll

import numpy as np
import datetime
from shapely.geometry import Polygon
import os.path

#load config
import yaml
app_config = yaml.load(file('predict_passes_config.yaml', 'r')) 

import argparse
parser = argparse.ArgumentParser(description='Predict passes for one day')

parser.add_argument('--ts', action="store")
parser.add_argument('--sat', action="store")

opts = parser.parse_args()
import datetime

pos_time = datetime.datetime.strptime(opts.ts, '%Y-%m-%dT%H:%M:%S')

platforms = app_config['platforms']
out_dir = app_config['out_dir']

tle_cache_file = "%s/%s-cache.tle" % (out_dir, pos_time.strftime('%Y%m%d'))

if not os.path.isfile(tle_cache_file): #cache tle in file
	print "no tle"
	exit()

tle =  read_tle_from_file_db(opts.sat, tle_cache_file, pos_time)

print "%.4f,%.4f" % get_avhrr_nadir_ll(tle, pos_time)