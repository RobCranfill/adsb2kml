#!/bin/bash
# get some kml - first arg is name of output file

wget localhost:8080 -O $1.kml
