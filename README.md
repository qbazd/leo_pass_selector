# LEO pass selector

LEO satellite pass selector over AOI.

This is test of library functions and usage example.

The test is done with AVHRR METOP-A.


Assumptions:
------------
- AOI can be defined as any custom Polygon (any valid shape will do).
- Selection can be done via cover area. One can select only full covered passes over AOI.
- Can be used in NearRealTime and reprocessing.
- Selection of passes via AOI cover percentage can be applied before or after prediction file save.
- Lib can write shapefiles of passes.


Stage one:
----------

1. Predict/generate most siutable passes for satellite over Area of Interest (AOI).
2. Save to predict file

Stage two:
----------

While EumetCast or other granule files are received:
1. Read prediction file
2. Match timeslots of granules with predictions 
3. Keep if matched else remove 


