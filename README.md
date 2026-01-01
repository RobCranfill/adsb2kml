# adsb2kml
Receive live ADS-B data from local aircraft, and display them in 3D via Google Earth.


# Concept of Operations
A Python web server runs a background task to collect aircraft data from an attached Software-Defined Radio.
It integrates this data, and on request from Google Earth, returns KML for display.


# Requirements
  * Python 
    * Python 3.13.7 used
    * Required libraries installed in a virtual environment
  * [py1090](https://py1090.readthedocs.io/en/latest/) python library 
  * [dump1090-fa](https://github.com/flightaware/dump1090) running as a web service.
  * Realtek SDR compatible with dump1090 ('Realtek Semiconductor Corp. RTL2838 DVB-T' used)
  * Google Earth (Google Earth Pro v7.3.6.10441 (64-bit) used)
  * This was all run under Ubuntu Linux 25.10


# Things to do
  * install dump1090 somewhere common (/home/rob/.local/bin?)
