# -*- coding: utf-8 -*-
"""Опрос GitHub за токеном device-flow (device_code передаётся аргументом)."""

import json
import sys
import time
import urllib.parse
import urllib.request

CLIENT = "178c6fc778ccc68e1d6a"
DEVICE = sys.argv[1]
URL = "https://github.com/login/oauth/access_token"

deadline = time.time() + 550
while time.time() < deadline:
    time.sleep(5)
    data = urllib.parse.urlencode(
        {"client_id": CLIENT, "device_code": DEVICE,
         "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}
    ).encode()
    req = urllib.request.Request(URL, data=data, headers={"Accept": "application/json"})
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=15))
    except Exception:
        continue
    if resp.get("access_token"):
        open("tools/gh_token.txt", "w").write(resp["access_token"])
        print("TOKEN-OK")
        break
    err = resp.get("error")
    if err in ("expired_token", "access_denied"):
        print("STOP:", err)
        break
else:
    print("TIMEOUT-NO-AUTH")
