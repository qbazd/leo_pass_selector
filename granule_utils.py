#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import datetime 
import numpy as np
from pyorbital import tlefile, orbital
from pyorbital.tlefile import Tle

#def read_all_tles_from_file(platform, tles_file):
#	platform = platform.strip().upper()
#	tles = []
#	fp = open(tles_file)
#	for l0 in fp:
#		l1, l2 = fp.next(), fp.next()
#		if l0.strip()[0:2] == '0 ' and l0.strip()[2:] == platform:
#			tles.append(Tle(platform, line1=l1, line2=l2))
#	fp.close()
#	return tles

#read_all_tles_from_file('METOP-A', 'current.tle')
#time_slot = datetime(2015, 01, 28, 00, 01, 3)
#print time_slot
#print 'check tles'
#print read_tle_from_file_db('METOP-A', 'current.tle',time_slot)

#tle cache
import requests
# gets tle from https://www.space-track.org
# tle from time_range_end -3 days .. time_range_end
def get_tle_spacetrack(time_range_end, noradids ,login, password):
	payload = {'identity' : login, 'password': password}
	base_url = "https://www.space-track.org"
	range_text = (time_range_end - datetime.timedelta(seconds=3600*24*3)).strftime('%Y-%m-%d') + "--" +  time_range_end.strftime('%Y-%m-%d')
	r1 = requests.post('%s/auth/login' % base_url, data= payload )
	tle_url = '%s/basicspacedata/query/class/tle/EPOCH/%s/NORAD_CAT_ID/%s/orderby/EPOCH ASC/format/3le' % (base_url, range_text, noradids)
	r2 = requests.get(tle_url, cookies=r1.cookies)
	if r2.status_code != 200:
		raise IOError('Spacetrack login error')
	#print (r1.status_code, r2.status_code)
	return r2.text
	
def read_tle_from_file_db(platform, tles_file, time_slot):
	import re
	platform = platform.strip().upper()
	tle = None
	last_tle = None
	fp = open(tles_file)
	for l0 in fp:
		l1, l2 = fp.next(), fp.next()
		if l0.strip() == platform or (l0.strip()[0:2] == '0 ' and l0.strip()[2:] == platform): # update for line 3 format 
			l1 = re.sub(r'\+(\d|\.)', ' \\1', l1) # hack for old tle files from 2012
			l2 = re.sub(r'\+(\d|\.)', ' \\1', l2) # hack for old tle files from 2012
			tle = Tle(platform, line1=l1, line2=l2) #read every tle and find the most suitable by the tle.epoch
			#print tle.epoch
			if tle.epoch > time_slot:
				return last_tle 
			last_tle = tle
	fp.close()
	if tle == None:
		return last_tle
	return tle

def get_avhrr_nadir_ll(tle, time_slot):
	from pyorbital.geoloc import ScanGeometry, compute_pixels, get_lonlatalt
	from pyorbital.geoloc_instrument_definitions import avhrr

	scan_geom = avhrr(1, np.array([1023]), decimate=0)
	s_times = scan_geom.times(time_slot)
	pixels_pos = compute_pixels((tle.line1, tle.line2), scan_geom, s_times)
	nadir_first_point = get_lonlatalt(pixels_pos, s_times)

	return nadir_first_point[0:2] 

def get_scan_avhrr_area(tle, time_slot, slots_count=1):
	from pyorbital.geoloc import ScanGeometry, compute_pixels, get_lonlatalt
	from pyorbital.geoloc_instrument_definitions import avhrr

	#first point used to normalize 
	scan_geom = avhrr(1, np.array([1023]), decimate=0)
	s_times = scan_geom.times(time_slot)
	pixels_pos = compute_pixels((tle.line1, tle.line2), scan_geom, s_times)
	nadir_first_point = get_lonlatalt(pixels_pos, s_times)

	scan_geom = avhrr((36 * slots_count)+1, np.array([0, 2047]), decimate=10)
	s_times = scan_geom.times(time_slot)
	pixels_pos = compute_pixels((tle.line1, tle.line2), scan_geom, s_times)
	pos_arr_edge = get_lonlatalt(pixels_pos, s_times)
	
	scan_geom = avhrr(2, np.arange(24, 2048, 40), decimate=36*10*slots_count )
	s_times = scan_geom.times(time_slot)
	pixels_pos = compute_pixels((tle.line1, tle.line2), scan_geom, s_times)
	pos_arr_ss = get_lonlatalt(pixels_pos, s_times)
	
	lines_edge = np.array([pos_arr_edge[0], pos_arr_edge[1]]).T
	lines_ss = np.array([pos_arr_ss[0], pos_arr_ss[1]]).T
	
	points_arr = np.concatenate( (lines_edge[0::2], lines_ss[pos_arr_ss[0].size/2:], lines_edge[-1::-2], lines_ss[:pos_arr_ss[0].size/2][::-1]))

	# normalize area aka dirty hack 
	if nadir_first_point[0][0] < -120.0:
		points_arr = map(lambda xy: xy if xy[0] < 120.0 else (xy[0] - 360.0, xy[1] ), points_arr)

	return points_arr

#time_slot = datetime(2015, 01, 28, 00, 01, 3)
#points_arr = get_scan_avhrr_area('METOP-A', time_slot)

from shapely.geometry import mapping,Polygon
import fiona
from fiona.crs import from_string
def write_shp(filename, schema, features, crs_string):
	crs_ = from_string(crs_string)
	with fiona.open(filename, 'w', 'ESRI Shapefile', schema=schema, crs = crs_  ) as c:
		for feature in features:
			c.write(feature)

#schema = { 
#    'geometry': 'Polygon','properties': {'platform': 'str','time_slot': 'str','in_balt': 'int',},
#}
#features = [
#{
#		'geometry': mapping(Polygon(balt_arr)),
#		'properties': {'platform': 'balt', 'time_slot': "", 'in_balt': 1},
#	},
#	]
#write_shp("out.shp", schema, features)

# platform is TLE platform
# aoi_polygon is shapely plygon 
# aoi_polygon_proj is projection in meters of aoi to compute area
# time_range_start datetime
# time_range_end datetime

from shapely.geometry import mapping, Polygon
from shapely.ops import transform
from shapely.geos import TopologicalError

from functools import partial
import pyproj
from geopy.distance import great_circle

def generate_avhrr_platform_passes_over_aoi(platform_tle, aoi_polygon, aoi_polygon_proj_string, time_range_start, time_range_end, max_distance_km):

	ll_proj = pyproj.Proj(init='epsg:4326')
	aoi_polygon_proj = pyproj.Proj(aoi_polygon_proj_string)

	ll2aoi_partial = partial(pyproj.transform,ll_proj,aoi_polygon_proj)
	aoi2ll_partial = partial(pyproj.transform,aoi_polygon_proj,ll_proj)

	aoi_area = aoi_polygon.area / 1000000
	
	aoi_centroid_ll = transform(aoi2ll_partial, aoi_polygon.centroid)

	aoi_timeslots = []
	current_pass = []

	granules_intersect_area = 0.0
	time_slot = time_range_start
	last_intersects = False

	while True:

		in_aoi = False

		# first, compute distance between aoi centroid and start of granule nadir 
		nadir_ll = get_avhrr_nadir_ll(platform_tle, time_slot)
		distance = great_circle(nadir_ll, (aoi_centroid_ll.x,aoi_centroid_ll.y)).km

		if distance < max_distance_km:
			#print "%s %.0f" % (time_slot.strftime('%Y-%m-%d %H:%M:%S UTC'), distance)
			granule_polygon = transform(ll2aoi_partial, Polygon(get_scan_avhrr_area(platform_tle, time_slot)))
			in_aoi = aoi_polygon.intersects(granule_polygon)

		if in_aoi == True:
			intersection_proj = aoi_polygon.intersection(granule_polygon)
			granules_intersect_area += intersection_proj.area / 1000000.0 # m^2 -> km^2
			current_pass.append(time_slot)

			#print "%s %d" % (time_slot.strftime('%Y-%m-%d %H:%M:%S UTC'), in_aoi)
			#print "%s,%.0f,%d" % (time_slot.strftime('%Y-%m-%d %H:%M:%S'), distance, in_aoi)


		if last_intersects == True and in_aoi == False: # pass ends
			int_percent = (granules_intersect_area / aoi_area * 100.0)

			if len(current_pass) > 0 and int_percent > 0.0:
				aoi_timeslots.append({ 'time_slot': current_pass[0], 'slots': len(current_pass), 'aoi_cover': int_percent})

			current_pass = []
			granules_intersect_area = 0.0

		if last_intersects == False and in_aoi == False and time_slot > time_range_end:
			break

		last_intersects = in_aoi
		time_slot = time_slot + datetime.timedelta(seconds=60)

	return aoi_timeslots

# gets granule pass over aoi from predicted aoi_timeslots list 
# if granule is not over aoi return None
def get_pass_for_granule(granule_time_slot_start, granule_time_slot_end,  aoi_timeslots):
	for aoit in aoi_timeslots:
		if granule_time_slot_start < aoit['time_slot'] and granule_time_slot_end > aoit['time_slot']:
			return aoit
		if granule_time_slot_start >= aoit['time_slot'] and granule_time_slot_start < (aoit['time_slot'] + datetime.timedelta(seconds = aoit['slots'] * 60) ):
			return aoit
	return None

# write sattelite passes as shapefile
def save_passes_as_shp(filemane, aoi_polygon, aoi_polygon_proj_string, aoi_timeslots, tles):
	from shapely.geometry import mapping, Polygon

	aoi_polygon_proj = pyproj.Proj(aoi_polygon_proj_string)

	schema = {'geometry': 'Polygon','properties': {'platform': 'str','time_slot': 'str','slots': 'int', 'cover': 'float'}}

	features = []

	for platform in aoi_timeslots.keys():
		for aoit in aoi_timeslots[platform]:
			poly = transform(aoi_polygon_proj, Polygon(get_scan_avhrr_area( tles[platform], aoit['time_slot'], aoit['slots'] )))
			feat = {'geometry': mapping(poly),'properties': {'platform': platform, 'time_slot': aoit['time_slot'].strftime('%Y-%m-%d %H:%M:%S UTC'), 'slots': aoit['slots'], 'cover': aoit['aoi_cover'] }}
			features.append(feat)

	feat = {'geometry': mapping(aoi_polygon),'properties': {'platform': "aoi", 'time_slot': "-", 'slots': 0, 'cover': -999  }}
	features.append(feat)

	write_shp(filemane, schema, features, aoi_polygon_proj_string)
