#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   Simple REST HTTP Weather Server using DWD weather data for Germany
#   Copyright (C) 2016 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import http.server
import json
import urllib.parse
import socketserver

import logging
logger = logging.getLogger("pydwdapi")


def create_server(api, port=8080, interface="127.0.0.1"):
    """
    Creates a new HTTP server instance which serves api requests.

    api : PyDWDApi
        Instance of the PyDWDApi class from which the data is read.
    port : int
        Port number on which the HTTP server should listen.
    interface : str
        Local ip address of the network interface the HTTP server should listen
        on.
    """

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send_json(self, http_code, obj):
            self.send_response(http_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    obj, indent=2, sort_keys=True).encode("utf-8"))

        def _error(self, http_code, msg):
            self._send_json(http_code, {"error": msg})

        def do_GET(self):
            def interpolate(tar, key, key_tar=None):
                key_tar = key if key_tar is None else key_tar
                try:
                    res, res_ts = api.interpolate_observations(key, lat, lon,
                                                               alt)
                    tar[key_tar] = round(res[0][0], 2)
                    response["dt"] = max(res_ts, response["dt"])
                except Exception:
                    pass

            response = {"coord": {}, "main": {}, "wind": {}, "dt": 0.0}
            try:
                # Make sure the URL is correct
                o = urllib.parse.urlparse(self.path)
                if o.path != "/api/1.0/weather":
                    self._error(404,
                                "Requested file " + o.path + " not found!")
                    return

                # Make sure the query is correct
                q = urllib.parse.parse_qs(o.query, keep_blank_values=True)
                try:
                    lat = float(q["lat"][0])
                    lon = float(q["lon"][0])
                    if "alt" in q:
                        alt = float(q["alt"][0])
                    else:
                        if api.altitude_data.in_bounds(lat, lon):
                            alt = round(
                                api.altitude_data.query(lat, lon)[0], 2)
                        else:
                            self._error(
                                400,
                                "No altitude data available for given point, please specify explicitly!")
                            return
                except Exception:
                    logger.exception("Error while parsing the arguments")
                    self._error(400, "Invalid query")
                    return

                # Write the coordinates
                response["coord"] = {
                    "alt": float(alt),
                    "lat": float(lat),
                    "lon": float(lon)
                }

                # Query the weather data and add it to the response
                api.update()

                # Add the weather data to the response
                interpolate(response["main"], "temperature", "temp")
                interpolate(response["main"], "pressure")
                interpolate(response["main"], "humidity")
                interpolate(response["main"], "precipitation")
                interpolate(response["wind"], "wind_speed", "speed")
                interpolate(response["wind"], "wind_speed_max", "max")
                interpolate(response["wind"], "wind_direction", "deg")

            except:
                logger.exception("Error while processing the request")
                self._error(500, "Internal error")
                return

            self._send_json(200, response)

    class Server(socketserver.TCPServer):
        allow_reuse_address = True
        timeout = 60.0

        def handle_timeout(self):
            try:
                api.update()
            except Exception:
                logger.exception("Exception while updating the data")

    # Create the server and return it
    httpd = Server((interface, port), Handler)
    return httpd

