#!/usr/bin/python
#
# prepares the bicycle parking POIs of OGD Wien for use with OSM applications.
#
# Written by Stefan Tauner, GPL3+ (if anyone asks)

import ogr, zipfile, shutil, os, sys, urllib2, subprocess

def main():
	ogr.UseExceptions()
	# There is an API call for this, but the python binding seems to be broken :/
	def cloneFieldDefn(src_def):
		fdef = ogr.FieldDefn(src_fd.GetName(), src_fd.GetType())
		fdef.SetWidth(src_fd.GetWidth())
		fdef.SetPrecision(src_fd.GetPrecision())
		return fdef

	ogr2osm_path = "ogr2osm/"
	wd = "wd/" # the working directory
	url = "http://data.wien.gv.at/daten/geoserver/ows?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:FAHRRADABSTELLANLAGEOGD&srsName=EPSG:4326&outputFormat=shape-zip"

	base_name = "FAHRRADABSTELLANLAGEOGD"
	zipname = base_name + ".zip"
	tbl = "conv"
	in_file = wd + "/orig/" + base_name + ".shp"
	out_file = wd + tbl + '/' + base_name + ".shp"

	if not os.path.exists(zipname):
		print "Zip file not there, downloading it"
		try:
			r = urllib2.urlopen(url)
			f = open(zipname, 'wb')
			f.write(r.read())
			f.close()
		except Exception as e:
			print "Could not download '%s':" % url
			exit(e)
	else:
		print "Using existing zip file"

	# get rid of previous converts
	shutil.rmtree(wd, True)

	# extract source zip
	try:
		with zipfile.ZipFile(zipname, 'r') as zip:
			zip.extractall(wd + "orig")
	except Exception as e:
		print "Could not extract '%s':" % zipname
		exit(e)

	# open original shapefile and copy it to new datasource
	try:
		drv = ogr.GetDriverByName("ESRI Shapefile")
		orig = drv.Open(in_file, 0)
	except Exception as e:
		print("Could not load input file: %s" % in_file)
		exit(e)
	print "Shapefile loaded successfully"

	ds = drv.CopyDataSource(orig, wd + tbl)
	layer = ds.GetLayer()
	layerdef = layer.GetLayerDefn()

	# get rid of unused fields
	layer.DeleteField(layerdef.GetFieldIndex("BEZIRK"))
	layer.DeleteField(layerdef.GetFieldIndex("ADRESSE"))

	# rename ANZAHL to capacity and make it int (looks complicated... alternative?)
	i = layerdef.GetFieldIndex("ANZAHL")
	src_fd = layerdef.GetFieldDefn(layerdef.GetFieldIndex("ANZAHL"))
	fdef = cloneFieldDefn(src_fd)
	fdef.SetName("capacity")
	fdef.SetType(ogr.OFTInteger)
	layer.AlterFieldDefn(i, fdef, (ogr.ALTER_NAME_FLAG | ogr.ALTER_WIDTH_PRECISION_FLAG))

	# add amenity field and populate it with bicycle_parking
	layer.CreateField(ogr.FieldDefn("amenity", ogr.OFTString))
	for i in range(layer.GetFeatureCount()):
		feat = layer.GetFeature(i)
		feat.SetField(layerdef.GetFieldIndex("amenity"), "bicycle_parking")
		layer.SetFeature(feat)

	ds.SyncToDisk()
	ds.Destroy()
	print "Transformation done"

	if find_ogr2osm(ogr2osm_path) != None:
		print "Calling ogr2osm"
		try:
			p = subprocess.Popen(["python", ogr2osm_path + "ogr2osm.py", out_file, "-e", "4326", "-f"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			out, bla = p.communicate()
		except Exception as e:
			print "ogr2osm failed:"
			exit(e)
		if p.returncode != 0:
			print "ogr2osm failed, output was:"
			print out,
	else:
		print "You need to create the OSM XML yourself, sorry."
		print "The converted files can be found in '%s'." % os.path.dirname(out_file)
	print "Done."

def find_ogr2osm(ogr2osm_path):
	path = ogr2osm_path + "ogr2osm.py"
	if not os.path.exists(path):
		print "ogr2osm.py not found, trying with git"
		ret = subprocess.call("git submodule update --init", shell=True)
		if not os.path.exists(path):
			print "nope"
			return None
	return path

if __name__ == "__main__":
	main()
