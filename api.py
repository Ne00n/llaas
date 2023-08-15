#!/usr/bin/python3
from bottle import HTTPResponse, route, run, request, template
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, pyasn, sqlite3, time, re
from pathlib import Path

def validateToken(token=''):
    for name,details in config['workers'].items():
        if details['token'] == token: return True

@route('/job/<token>', method='GET')
def index(token=''):
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",token,re.MULTILINE | re.DOTALL)
    if not token or not validateToken(token[0]): return HTTPResponse(status=400, body={"error":"Invalid Token"})
    mutex.acquire()
    response = {}
    for ip, request in requests.items():
        print(request)
        if request["status"] == "accepted":
            requests[ip]["status"] = "assigned"
            response = requests[ip]
            break
    mutex.release()
    return HTTPResponse(status=200, body=response)

@route('/job/<token>', method='POST')
def index(token=''):
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",token,re.MULTILINE | re.DOTALL)
    if not token or not validateToken(token[0]): return HTTPResponse(status=400, body={"error":"Invalid Token"})
    payload = json.load(request.body)
    mutex.acquire()
    ip = list(payload.keys())[0]
    requests[ip] = payload
    mutex.release()
    return HTTPResponse(status=200, body={})

@route('/<request>', method='GET')
def index(request=''):
    if len(request) > 100: return HTTPResponse(status=414, body={"data":"way to fucking long"})
    request = request.replace("/","")
    ipv4 = re.findall("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",request, re.MULTILINE)
    if ipv4:
        asndata = asndb.lookup(ipv4[0])
        if asndata[0] is None: return HTTPResponse(status=400, body={"data":"invalid IPv4"})
        connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True)
        response = list(connection.execute("SELECT * FROM requests WHERE subnet = ?",(asndata[1],)))
        print(response)
        expiry = int(time.time()) + 60
        if not response:
            connection.execute(f"INSERT INTO requests VALUES ('{asndata[1]}','0','{expiry}')")
            connection.commit()
            connection.close()
            return HTTPResponse(status=200)
        return HTTPResponse(status=200, body={"subnet":response[0][0]})
    else:
        return HTTPResponse(status=400, body={"data":"invalid IPv4"})

print("Preparing sqlite3")
connection = sqlite3.connect("file:subnets?mode=memory&cache=shared", uri=True)
connection.execute("""CREATE TABLE requests (subnet, status, expiry)""")
connection.execute("""CREATE TABLE results (subnet, worker, latency, FOREIGN KEY(subnet) REFERENCES requests(subnet) ON DELETE CASCADE)""")
print("Loading config")
with open('api.json') as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn('asn.dat')
print("Ready")

run(host="::", port=8080, server='paste')