#!/usr/bin/python3
from bottle import HTTPResponse, route, run, request, template
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, pyasn, sqlite3, time, re, os
from pathlib import Path

fullPath = os.path.realpath(__file__).replace("api.py","")

def validate(payload):
    if not "token" in payload or not "worker" in payload: return False
    if not re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL): return False
    if not re.findall(r"^([A-Za-z0-9.=+-]{3,50})$",payload['worker'],re.MULTILINE | re.DOTALL): return False
    for worker,details in config['workers'].items():
        if worker == payload['worker'] and details['token'] == payload['token']: return True

def getConnection():
    connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True, isolation_level=None, timeout=10)
    connection.execute('PRAGMA journal_mode = WAL;')
    connection.execute('PRAGMA foreign_keys = ON;')
    connection.commit()
    return connection

def query(request,pings):
    if len(request) > 100: return HTTPResponse(status=414, body={"data":"way to fucking long"})
    request = request.replace("/","")
    ipv4 = ipRegEx.findall(request)
    if not ipv4: return HTTPResponse(status=400, body={"data":"invalid IPv4"})
    result = pingsRegEx.findall(pings)
    if not result: return HTTPResponse(status=400, body={"data":"Invalid Amount of Pings"})
    asndata = asndb.lookup(ipv4[0])
    if asndata[0] is None: return HTTPResponse(status=400, body={"data":"invalid IPv4"})
    connection = getConnection()
    response = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency,requests.expiry FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = ? ORDER BY results.latency",(asndata[1],)))
    if response and int(time.time()) > int(response[0][4]):
        connection.execute(f"DELETE FROM requests WHERE subnet = ?",(response[0][0],))
        connection.commit()
        response = {}
    if not response:
        expiry = int(time.time()) + 1800
        connection.execute(f"INSERT INTO requests (subnet, ip, expiry) VALUES (?,?,?)",(asndata[1],ipv4[0], expiry))
        for worker,details in config['workers'].items():
            pings = round(float(pings) / 2)
            for run in range(pings): connection.execute(f"INSERT INTO results (subnet, worker) VALUES (?,?)",(asndata[1], worker))
        connection.commit()
        response = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = ?",(asndata[1],)))
    connection.close()
    data = {}
    for row in response:
        if not row[2] in data: data[row[2]] = {"pings":[]}
        data[row[2]]["pings"].append(row[3])
        if row[3] is None: 
            data = {}
            break
    return {"subnet":response[0][0],"ip":response[0][1],"data":data}

@route('/job/get', method='POST')
def index():
    payload = json.load(request.body)
    if not validate(payload): return HTTPResponse(status=401, body={"error":"Invalid Auth"})
    connection = getConnection()
    ips = list(connection.execute("SELECT results.id,requests.subnet,requests.ip,results.worker FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE results.worker = ? AND results.latency is NULL LIMIT 1000",(payload['worker'],)))
    connection.close()
    return {"ips":ips}

@route('/job/deliver', method='POST')
def index():
    payload = json.load(request.body)
    if not validate(payload): return HTTPResponse(status=401, body={"error":"Invalid Auth"})
    connection = getConnection()
    for subnet,details in payload['data'].items():
        connection.execute(f"UPDATE results SET latency = ? WHERE subnet = ? and worker = ? and id = ?",(details['latency'],subnet,payload['worker'],details['id'],))
    connection.commit()
    connection.close()
    return HTTPResponse(status=200, body={})

@route('/<request>/<pings>', method='GET')
def index(request='',pings="2"):
    return query(request,pings)

@route('/<request>', method='GET')
def index(request=''):
    return query(request,"2")

print("Preparing sqlite3")
connection = getConnection()
connection.execute("""CREATE TABLE requests (subnet PRIMARY KEY, ip, expiry)""")
connection.execute("""CREATE TABLE results (id INTEGER NOT NULL PRIMARY KEY, subnet, worker, latency DECIMAL(3,2) DEFAULT NULL, FOREIGN KEY(subnet) REFERENCES requests(subnet) ON DELETE CASCADE)""")
connection.commit()
print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn(f"{fullPath}asn.dat")
print("Preparing regex")
ipRegEx = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
pingsRegEx = re.compile("^([1-9]|[1-9][0])$")
print("Ready")

run(host="127.0.0.1", port=8080, server='gunicorn')