#!/usr/bin/python3
import requests, subprocess, json, time, math, ssl, sys, re, os

fullPath = os.path.realpath(__file__).replace("worker.py","")

print("Loading worker.json")
with open(f"{fullPath}configs/worker.json") as handle: config = json.loads(handle.read())

def call(url,payload):
    for run in range(4):
        try:
            print(f"Fetching {url}")
            response = requests.post(url, data=json.dumps(payload),timeout=(3, 3))
            if (response.status_code == 200):
                return response.json()
            else:
                print(f"Got {response.status_code} with {response.text}")
        except Exception as e:
            print(f"Error {e}")
            time.sleep(5)
    return {'ips':[]}

batchSize = 250
while True:
    data = call(f"{config['api']}/job/get",config)
    print(f"Got {len(data['ips'])} IP's")
    if len(data['ips']) > 0:
        rounds = int(math.ceil(len(data['ips']) / batchSize))
        for run in range(rounds):
            print(f"Running batch {run} of {rounds}")
            ips,mapping = [],{}
            for row in data['ips'][:batchSize]:
                ips.append(row['ip'])
                mapping[row['ip']] = row

            fping = f"fping -c 1 "
            fping += " ".join(ips)

            p = subprocess.run(fping, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            parsed = re.findall("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*?(min/avg/max) = [0-9.]+/([0-9.]+)",p.stderr.decode('utf-8'), re.MULTILINE)

            response = config
            response["data"] = {}
            for row in parsed:
                currentIP = row[0]
                subnet = mapping[currentIP]['subnet']
                response["data"][subnet] = {"ip":currentIP,"latency":row[2]}

            for row in data['ips'][:batchSize]:
                if not row['subnet'] in response['data']: response["data"][row['subnet']] = {"id":row['ID'],"ip":row['ip'],"latency":-1}
        data = call(f"{config['api']}/job/deliver",response)
    else:
        time.sleep(10)