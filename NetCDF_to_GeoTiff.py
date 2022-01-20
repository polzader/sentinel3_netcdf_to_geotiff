#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
#sys.path.append('/home/pablo/.snap/snap-python')
import os
from snappy import ProductIO #, HashMap, GPF
import geopandas as gpd
import numpy as np
import subprocess
import getopt
from zipfile import ZipFile

def unzip(zip_file):

	if os.path.exists(zip_file):
		with ZipFile(zip_file, 'r') as zip_ref:
			extracted = zip_ref.namelist()
			zip_ref.extractall(os.path.dirname(zip_file))

		extracted_file = os.path.join(os.path.dirname(zip_file), extracted[0])

		if os.path.isdir(extracted_file):
			return extracted_file
		else:
			print(f'Cant extract ZIP file {zip_file}. Check permission.')
			return None
	else:
		print(f'Zip file {zip_file} does not exist')
		return None

def remove_shape(folder):

	files_in_directory = os.listdir(folder)
	files = [file for file in files_in_directory if file.endswith(".shp") or file.endswith(".dbf") or file.endswith(".shx") or file.endswith(".prj") or  file.endswith(".cpg")]
	if len(files) != 0:
		for f in files:
			os.remove(folder+'/'+f)


def main(argv):

	if len(argv) == 0:
		print(f'\n The correct way to use this script is: \n NetCDF_to_GeoTiff.py --input=<Full_path_to_ZIP_product> --output=<Full_path_to_Output_dir>')
		sys.exit(2)
	#parse line command
	try:
		opts, args = getopt.getopt(argv,"h",["input=","output="])
	except getopt.GetoptError:
		print(f'\n NetCDF_to_GeoTiff.py --input=<Full_path_to_ZIP_product> --output=<Full_path_to_Output_dir>')
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print(f'\n NetCDF_to_GeoTiff.py --input=<Full_path_to_ZIP_product> --output=<Full_path_to_Output_dir>')
			sys.exit()
		elif (opt in ("--input")):
			input_file = arg
		elif (opt in ("--output")):
			output_dir = arg
		else:
			print(f'\n The correct way to use this script is: \n NetCDF_to_GeoTiff.py -i or --input=<Full_path_to_ZIP_product> -o or --output=<Full_path_to_Output_dir>')
			sys.exit(2)

	#checking
	if not os.path.exists(output_dir):
		print(f'\n Output directory {output_dir} must be a valid path.')
		sys.exit(2)

	#unzip product
	img = unzip(input_file)
	if img is None:
		sys.exit(2)

	path_output = output_dir

	#Reading product XML
	prod = ProductIO.readProduct(img)

	if prod is None:
		print(f'Cant read XML file or not exist.')
		sys.exit(2)

	bands = list(prod.getBandNames())

	for i,b in enumerate(bands):
		print(f'{i}. {b}')

	# Get input paramenter command line
	var = input("For a variable select its number or * to select all bands: ")

	if var.isnumeric():
		if  (0 <= int(var)) and (int(var) <= len(bands)-1):
			var = [bands[int(var)]]
		else:
			print("Index out range")
			sys.exit(2)

	elif var in bands:
		var = [var]
	elif var=='*':
		var = bands
	else:
		print(f'Band {var} is not in dataset')
		sys.exit(2)

	EPSG=4326

	#Begin processing
	for v in var:

		print(f'Processing  {v} ...')
		suffix = v.split('_')

		if len(suffix) > 1:
			suffix=suffix[-1]
		else:
			suffix='in'

		lat = prod.getBand('latitude_'+suffix)
		lon = prod.getBand('longitude_'+suffix)
		cols, rows = (prod.getSceneRasterWidth(), prod.getSceneRasterHeight())
		lat_band = np.zeros(cols*rows, np.float32)
		lat.readPixels(0, 0, cols, rows, lat_band)
		lat_n = np.max(lat_band)
		lat_s = np.min(lat_band)
		lon_band = np.zeros(cols*rows, np.float32)
		lon.readPixels(0, 0, cols, rows, lon_band)
		lon_e = np.max(lon_band)
		lon_w = np.min(lon_band)
		band = prod.getBand(v)
		dtype = band.getDataType()
		add_val = band.getScalingOffset()
		mult_val = band.getScalingFactor()
		v_band = np.zeros(cols*rows, np.float32)
		band.readPixels(0, 0, cols, rows, v_band)
		noData = band.getNoDataValue()
		noData = noData*mult_val+add_val
		gdf = gpd.GeoDataFrame(v_band, geometry=gpd.points_from_xy(lon_band, lat_band), crs=EPSG)
		v_name= v[:10]
		gdf = gdf.rename(columns={0:v_name})
		gdf = gdf[~((noData-0.001<gdf[v_name]) & (gdf[v_name]<noData+0.001))]
		shape_fullname = path_output+'/'+v+'.shp'
		geotiff_output = path_output+'/'+v+'.tif'
		geotiff_fullname = path_output+'/'+v+'_.tif'
		geotiff_input = geotiff_fullname

		print(f'Generating product: {v}')
		print(f'\n Cols: {cols} \n Rows:{rows} \n SRC: {EPSG} \n BoundingBox(west south east north): {lon_w} {lat_s} {lon_e} {lat_n} \n')

		if not gdf.empty:

			gdf.to_file(shape_fullname)

			# rasterize
			#gdal_rasterize -a_srs EPSG:4326 -l LST -a Z -ts cols rows -a_nodata -32768.0 -te 8.66995 49.3738 37.1046 62.9177 -ot Float32 -of GTiff /home/pablo/upwork/data/outputs/LST.shp /tmp/processing_249741b0b46444429f23cd54489b3867/ccd313605eaa4395aaf0b0768c1bc923/OUTPUT.tif
			try:
				gdal_rasterize_cmd = 'gdal_rasterize'
				print(f'Generating GeoTIFF file {geotiff_fullname}...')
				cmd_rasterize = '{} -a_srs EPSG:4326 -l {} -a {} -ts {} {} -a_nodata -32768.0 -te {} {} {} {} -ot Float32 -of GTiff {} {}' \
									.format(gdal_rasterize_cmd, v, v_name ,cols, rows, lon_w, lat_s, lon_e, lat_n, shape_fullname, geotiff_fullname)
				proc=subprocess.Popen(cmd_rasterize, bufsize=0, executable=None, stdin=None, stdout=subprocess.PIPE,
													stderr=subprocess.PIPE, preexec_fn=None,close_fds=True, shell=True)
				proc.wait()
				out, err=proc.communicate()
				print(out)
				print(err)
			except Exception(e):
				print(f'Cant execute {cmd_rasterize}. Error: {str(e)}')
				remove_shape(path_output)
				sys.exit(2)

			# filldata
			#gdal_fillnodata.py -md 2 input.tif output.tif
			try:
				gdal_fillnodata_cmd = 'gdal_fillnodata.py'
				cmd_filldata = '{} -md 2 {} {}'.format(gdal_fillnodata_cmd, geotiff_input, geotiff_output)
				proc=subprocess.Popen(cmd_filldata, bufsize=0, executable=None, stdin=None, stdout=subprocess.PIPE,
													stderr=subprocess.PIPE, preexec_fn=None,close_fds=True, shell=True)
				proc.wait()
				out, err=proc.communicate()
				print(out)
				print(err)

			except Exception(e):
				print(f'Cant execute {cmd_filldata}. Error: {str(e)}')
				remove_shape(path_output)
				if os.path.exists(geotiff_output):
					os.remove(geotiff_output)
					sys.exit(2)
		else:
			print(f'Warn. DataFrame of {v} empty, cant save.')

		remove_shape(path_output)
		if os.path.exists(geotiff_output):
			os.remove(geotiff_fullname)

		print('-------------------------------------------------------')


if __name__ == "__main__":

	main(sys.argv[1:])
