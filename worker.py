#!/usr/bin/python3
import requests, subprocess, json, time, ssl, sys, re, os

fullPath = os.path.realpath(__file__).replace("worker.py","")

print("Loading worker.json")
with open(f"{fullPath}worker.json") as handle: config = json.loads(handle.read())

def error(run):
    print(f"Retrying {run+1} of 4")
    if run == 3:
        print("Aborting, limit reached.")
        exit()
    time.sleep(2)

url = f"{config['api']}/job"   

ctx = ssl.create_default_context()
#ctx.check_hostname = False
#ctx.verify_mode = ssl.CERT_NONE

for run in range(4):
    try:
        target = f"{url}/get"
        print(f"Fetching {target}")
        response = requests.post(target, data=json.dumps(config))
        if (response.status_code == 200):
            json = response.json()
            break
        else:
            print("Got non 200 response code")
            error(run)
    except Exception as e:
        print(f"Error {e}")
        error(run)

print(json)