Using Image FROM mundialis/esa-snap:ubuntu (2.5GB)

# Install
cd docker
docker build -t snap-snappy .

# Run 

docker run -v /Full_path_on_host_data:/folder_in_container -it snap-snappy  NetCDF_to_GeoTiff.py \
	--input=/folder_in_container/S3B_SL_2_LST____20210906T090826_20210906T091126_20210906T113658_0179_056_321_1980_LN2_O_NR_004.zip \
	--output=/folder_in_container



# Example:
docker run -v /home/pablo/Descargas:/Descargas -it snap-snappy  NetCDF_to_GeoTiff.py \ 
		--input=/Descargas/S3B_SL_2_LST____20210906T090826_20210906T091126_20210906T113658_0179_056_321_1980_LN2_O_NR_004.zip \ 
		--output=/Descargas

