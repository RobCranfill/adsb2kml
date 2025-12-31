
from http.server import BaseHTTPRequestHandler, HTTPServer
import random
import time
import threading

import py1090


# needed? i think not
DUMP_COLLECTION_SLEEP_SEC = .1

# Stop drawing an a/c if we don't see it in this many seconds
AP_TIME_EXPIRE = 15

# Key: ICAO hex id; value: callsign_info
_hex_to_callsign  = {}
DROP_CS_AFTER = 30 # if we haven't seen a given callsign in this many seconds
_show_callsigns_ = True


_airplanes = dict()
_all_messages = 0
_ok_messages = 0


# FIXME
_print_once = True


################################################### classes


class KMLACServer(BaseHTTPRequestHandler):
    """Class to serve aircraft KML data to GE."""

    global _airplanes

    def do_GET(self):

        print("got a GET request...")
        print(f"{_airplanes}")

        self.send_response(200)

        # print('Content-Type: application/vnd.google-earth.kml+xml\n')
        self.send_header("Content-type", "application/vnd.google-earth.kml+xml")
        self.end_headers()

        self.wfile.write(bytes('<?xml version="1.0" encoding="UTF-8"?>', "utf-8"))
        self.wfile.write(bytes('<kml xmlns="http://www.opengis.net/kml/2.2">', "utf-8"))
        self.wfile.write(bytes('<Document>', "utf-8"))

        for ap in _airplanes.values():

            dump = ap.dump_msg
            # print(f"make kml for {dump}")
            lat = ap.dump_msg.latitude
            lon = ap.dump_msg.longitude
            alt = ap.dump_msg.altitude
            id = ap.dump_msg.hexident

            apkml = floating_placemark(lat, lon, alt, id)

            self.wfile.write(bytes((apkml), "utf-8"))

        self.wfile.write(bytes('</Document>', "utf-8"))
        self.wfile.write(bytes('</kml>', "utf-8"))


def floating_placemark(lat, lon, alt, id_str):
    """"Return the kml"""

    result  = "<Placemark>\n"
    result +=  f"<name>{id_str}</name>\n"

        #  " <visibility>0</visibility>\n" +
        #  " <description>Floats a defined distance above the ground.</description>\n" +
        #  " <LookAt>\n" +
        # f"  <longitude>{lon}</longitude>\n" +
        # f"  <latitude>{lat}}</latitude>\n" +
        #  "  <altitude>{alt}</altitude>\n" +
        #  "  <heading>0</heading>\n" +
        #  "  <tilt>0</tilt>\n" +
        #  "  <range>500</range>\n" +
        #  " </LookAt>\n" +

    result +=   "<styleUrl>#downArrowIcon</styleUrl>\n"
    result +=  "<Point>\n"
    result +=  " <altitudeMode>relativeToGround</altitudeMode>\n"
    result +=  f"<coordinates>{lon},{lat},{alt}</coordinates>\n"
    result +=  "</Point>\n"
    result +=  "</Placemark>\n"

    return result


class ap_info():
    """The a/c dump1090 record, and the last time we got data for this a/c.
    We keep a dictionary of this info, keyed on 'hexident' value. """

    def __init__(self, dump_msg, last_seen_time):
        """dump_msg is the entire dump1090 record."""
        self.dump_msg = dump_msg
        self.last_seen_time = last_seen_time
        self.callsign = None

    def __str__(self):
        return f"{self.dump_msg.hexident}/{self.callsign}"

    def __repr__(self):
        """Used by {x=} formatting!"""
        return self.__str__()

    def set_callsign(self, callsign):
        global _hex_to_callsign

        self.callsign = callsign
        _hex_to_callsign[self.dump_msg.hexident] = callsign_info(callsign)
        print(f" Callsigns: {_hex_to_callsign}")


class callsign_info():
    """Similiarly, a record of a callsign and the last time we saw/used it.
    To be put in a dictionary wherein the key is the ICAO number ("hexident")."""

    def __init__(self, callsign):
        self.callsign = callsign
        self.last_seen = time.monotonic()

    def __str__(self):
        return f"{self.callsign} @{int(self.last_seen)}"

    def __repr__(self):
        return self.__str__()


################################################### methods

def tidy_callsigns():
    keys_to_drop = []
    global _hex_to_callsign

    for hi, ci in _hex_to_callsign.items():
        if time.monotonic() - DROP_CS_AFTER > ci.last_seen:
            print(f" *** drop callsign {ci.callsign}")
            keys_to_drop.append(hi)

    for hi in keys_to_drop:
        del _hex_to_callsign[hi]


def doBackgroundTasks():
    """
        Maintain the backing data: a/c, callsigns
    """

    global _airplanes
    global _all_messages
    global _ok_messages
    global _print_once

    try:
        with py1090.Connection() as connection:
            print("dump1090 connection OK")
            for line in connection:

                # print(line)

                # Happens occasionally
                try:
                    msg = py1090.Message.from_string(line)
                except IndexError:
                    print("**** Error parsing message! Continuing....")
                    continue

                if msg.message_type == 'MSG':
                    _all_messages += 1

                    # Only track a/c we have lat/long for.
                    # FIXME: is this right?
                    #
                    if not None in [msg.hexident, msg.latitude, msg.longitude]:
                        _ok_messages += 1

                        # to see everthing, use this:
                        # print(f"  {msg.__dict__=}")

                        if _print_once:
                            print(f"{msg.__dict__}")
                            _print_once = False

                        hi = msg.hexident
                        if _airplanes.get(hi) is None:
                            print(f"\nNew a/c {hi}")
                            _airplanes[hi] = ap_info(msg, time.monotonic())
                            print(f"  {len(_airplanes)} {_airplanes=}")

                    # should we only process a/c with lat/long, or all?
                    # I think maybe often (always?) if we have lat/lon we DON"T have callsign!

                    # # do we have a callsign for this a/c?
                    # if msg.hexident is not None: # i've never seen this happen, but hey.
                    ac = _airplanes.get(msg.hexident)
                    if ac is not None:
                        cs = _airplanes[msg.hexident].callsign
                        # print(f"  (looking at old cs {cs})")
                        if cs is None and msg.callsign is not None:
                            cs = msg.callsign.strip()
                            print(f"\n  Got callsign for {msg.hexident=}: {cs}")
                            ac.set_callsign(cs)
                            print(f"  a/c now {ac}")
                            print(f" {_airplanes=}")

                # clean up callsign dict, else will grow forever
                tidy_callsigns()


        time.sleep(DUMP_COLLECTION_SLEEP_SEC)

    except ConnectionRefusedError:
        print("Can't connect! Is dump1090 running?")
        keep_running = False


# init data collection thread as deamon
d = threading.Thread(target=doBackgroundTasks, name='Daemon')
d.daemon = True
d.start()

# run the HTTP server
hostName = "localhost"
serverPort = 8080

webServer = HTTPServer((hostName, serverPort), KMLACServer)
print(f"Server started http://{hostName}:{serverPort}")

try:
    webServer.serve_forever()
except KeyboardInterrupt:
    pass

webServer.server_close()
print("Server stopped.")
