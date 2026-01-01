#!/bin/bash
# start the main python code
# assumes the dump1090 daemon is running

. env/bin/activate
python3 adsbkml.py

