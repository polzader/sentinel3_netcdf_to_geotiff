
FROM mundialis/esa-snap:ubuntu
LABEL maintainer="Pablo Zader <pzader@gmail.com>"
RUN apt-get -y update
RUN apt-get -y install python-gdal
RUN apt-get -y install gdal-bin

RUN python3 -m pip install --upgrade pip

RUN pip3 install geopandas

WORKDIR /data
COPY . .
ENTRYPOINT ["python3"]




