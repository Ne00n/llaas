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

def call(url,payload):
    for run in range(4):
        try:
            print(f"Fetching {url}")
            response = requests.post(url, data=json.dumps(payload))
            if (response.status_code == 200):
                return response.json()
            else:
                print("Got non 200 response code")
                error(run)
        except Exception as e:
            print(f"Error {e}")
            error(run)

data = call(f"{config['api']}/job/get",config)
print(f"Got {len(data['ips'])} IP's")

ips,mapping = [],{}
for row in data['ips'][:100]: 
    ips.append(row[1])
    mapping[row[1]] = row[0]

fping = f"fping -c 2 "
fping += " ".join(ips)

p = subprocess.run(fping, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
parsed = re.findall("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*?(min/avg/max) = [0-9.]+/([0-9.]+)",p.stderr.decode('utf-8'), re.MULTILINE)

response = config
response["data"] = {}
for row in parsed:
    currentIP = row[0]
    subnet = mapping[currentIP]
    response["data"][subnet] = {"ip":currentIP,"latency":row[2]}

for row in data['ips'][:100]:
    response["data"][row[0]] = {"ip":row[1],"latency":False}

data = call(f"{config['api']}/job/deliver",response)
