#!/usr/bin/python3
from bottle import HTTPResponse, route, run, request, template
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, pyasn, sqlite3, time, re
from pathlib import Path

inboundQueue = []
def validateToken(token=''):
    for name,details in config['workers'].items():
        if details['token'] == token: return True

def validateWorker(worker=''):
    for name,details in config['workers'].items():
        if name == worker: return True

@route('/job/get', method='POST')
def index():
    payload = json.load(request.body)
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL)
    if not token or not validateToken(token[0]): return HTTPResponse(status=400, body={"error":"Invalid Token"})
    worker = re.findall(r"^([A-Za-z0-9/.=+]{3,60})$",payload['worker'],re.MULTILINE | re.DOTALL)
    if not worker or not validateWorker(worker[0]): return HTTPResponse(status=400, body={"error":"Invalid Worker"})
    ips = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE results.worker = ? AND results.latency is NULL",(payload['worker'],)))
    return HTTPResponse(status=200, body={"ips":ips})

@route('/job/deliver', method='POST')
def index():
    payload = json.load(request.body)
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL)
    if not token or not validateToken(token[0]): return HTTPResponse(status=400, body={"error":"Invalid Token"})
    worker = re.findall(r"^([A-Za-z0-9/.=+]{3,60})$",payload['worker'],re.MULTILINE | re.DOTALL)
    if not worker or not validateWorker(worker[0]): return HTTPResponse(status=400, body={"error":"Invalid Worker"})
    connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True, isolation_level=None, timeout=10)
    connection.execute('PRAGMA journal_mode=WAL;')
    connection.commit()
    for subnet,details in payload['data'].items():
        connection.execute(f"UPDATE results SET latency = ? WHERE subnet = ? and worker = ?",(details['latency'],subnet,payload['worker'],))
    connection.commit()
    connection.close()
    return HTTPResponse(status=200, body={})

@route('/<request>', method='GET')
def index(request=''):
    if len(request) > 100: return HTTPResponse(status=414, body={"data":"way to fucking long"})
    request = request.replace("/","")
    ipv4 = ipRegEx.findall(request)
    if ipv4:
        asndata = asndb.lookup(ipv4[0])
        if asndata[0] is None: return HTTPResponse(status=400, body={"data":"invalid IPv4"})
        connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True, isolation_level=None, timeout=10)
        connection.execute('PRAGMA journal_mode=WAL;')
        connection.commit()
        response = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency,requests.expiry FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = ?",(asndata[1],)))
        if response and int(time.time()) > int(response[0][4]):
            connection.execute(f"DELETE FROM requests WHERE subnet = ?",(response[0][0],))
            connection.commit()
            response = {}
        if not response:
            #set expiry to 6 hours
            expiry = int(time.time()) + 21600
            connection.execute(f"INSERT INTO requests (subnet, ip, expiry) VALUES (?,?,?)",(asndata[1],ipv4[0], expiry))
            for worker,details in config['workers'].items():
                connection.execute(f"INSERT INTO results (subnet, worker) VALUES (?,?)",(asndata[1], worker))
            connection.commit()
            response = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = ?",(asndata[1],)))
        connection.close()
        data = {}
        for row in response:
            if row[3] is None: 
                data = {}
                break
            data[row[2]] = row[3]
        return HTTPResponse(status=200, body={"subnet":response[0][0],"ip":response[0][1],"data":data})
    else:
        return HTTPResponse(status=400, body={"data":"invalid IPv4"})

print("Preparing sqlite3")
connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True, isolation_level=None)
connection.execute("""CREATE TABLE requests (subnet, ip, expiry)""")
connection.execute("""CREATE TABLE results (subnet, worker, latency DECIMAL(3,2) DEFAULT NULL, FOREIGN KEY(subnet) REFERENCES requests(subnet) ON DELETE CASCADE)""")
connection.execute('PRAGMA journal_mode=WAL;')
connection.commit()
print("Loading config")
with open('api.json') as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn('asn.dat')
print("Preparing regex")
ipRegEx = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
print("Ready")

run(host="127.0.0.1", port=8080, server='gunicorn')