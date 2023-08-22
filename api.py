#!/usr/bin/python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, pyasn, sqlite3, bottle, time, re, os
from pathlib import Path

fullPath = os.path.realpath(__file__).replace("api.py","")
app = bottle.Bottle()

def validate(payload):
    if not "token" in payload or not "worker" in payload: return False
    if not re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL): return False
    if not re.findall(r"^([A-Za-z0-9.=+-]{3,50})$",payload['worker'],re.MULTILINE | re.DOTALL): return False
    for worker,details in config['workers'].items():
        if worker == payload['worker'] and details['token'] == payload['token']: return True

def getConnection():
    connection = sqlite3.connect("file::memory:?cache=shared", uri=True, isolation_level=None)
    connection.execute('PRAGMA journal_mode = WAL;')
    connection.execute('PRAGMA foreign_keys = ON;')
    connection.commit()
    return connection

def insert(connection,subnet,ip,pings):
    expiry = int(time.time()) + 1800
    connection.execute(f"INSERT INTO requests (subnet, ip, expiry) VALUES (?,?,?)",(subnet,ip, expiry))
    for worker,details in config['workers'].items():
        for run in range(int(pings)): connection.execute(f"INSERT INTO results (subnet, worker) VALUES (?,?)",(subnet, worker))
    connection.commit()

def cleanUp(connection):
    connection.execute(f"DELETE FROM requests WHERE subnet = ?",(response[0][0],))
    connection.commit()

def query(request,pings):
    if len(request) > 100: bottle.abort(413,"Way to fucking long.")
    request = request.replace("/","")
    ipv4 = ipRegEx.findall(request)
    if not ipv4: bottle.abort(400,"Invalid IPv4 address.")
    result = pingsRegEx.findall(pings)
    if not result: bottle.abort(400,"Invalid Amount of Pings.")
    asndata = asndb.lookup(ipv4[0])
    if asndata[0] is None: bottle.abort(400,"Unable to lookup IPv4 address.")
    connection = getConnection()
    response = list(connection.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency,requests.expiry FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = ? ORDER BY results.ROWID",(asndata[1],)))
    if response and int(time.time()) > int(response[0][4]):
        cleanUp(connection)
        response = {}
    if not response:
        insert(connection,asndata[1],ipv4[0],pings)
        connection.close()
        return {"subnet":asndata[1],"ip":ipv4[0],"data":{}}
    else:
        connection.close()
        data = {}
        for row in response:
            if not row[2] in data: data[row[2]] = []
            data[row[2]].append(row[3])
        return {"subnet":asndata[1],"ip":ipv4[0],"data":data}

@app.route('/job/get', method='POST')
def index():
    payload = json.load(bottle.request.body)
    if not validate(payload): bottle.abort(401,"Invalid Auth")
    connection = getConnection()
    ips = list(connection.execute("SELECT results.ROWID,requests.subnet,requests.ip,results.worker FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE results.worker = ? AND results.latency is NULL GROUP BY requests.subnet LIMIT 1000",(payload['worker'],)))
    connection.close()
    return {"ips":ips}

@app.route('/job/deliver', method='POST')
def index():
    payload = json.load(bottle.request.body)
    print(payload)
    if not validate(payload): bottle.abort(401,"Invalid Auth")
    connection = getConnection()
    for subnet,details in payload['data'].items():
        connection.execute(f"UPDATE results SET latency = ? WHERE subnet = ? and worker = ? and ROWID = ?",(details['latency'],subnet,payload['worker'],details['id'],))
    connection.commit()
    connection.close()
    return {}

@app.route('/<request>/<pings>', method='GET')
def index(request='',pings="2"):
    return query(request,pings)

@app.route('/<request>', method='GET')
def index(request=''):
    return query(request,"2")

print("Preparing sqlite3")
connection = getConnection()
connection.execute("""CREATE TABLE requests (subnet PRIMARY KEY, ip, expiry)""")
connection.execute("""CREATE TABLE results (subnet, worker, latency DECIMAL(3,2) DEFAULT NULL, FOREIGN KEY(subnet) REFERENCES requests(subnet) ON DELETE CASCADE)""")
connection.commit()
print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn(f"{fullPath}asn.dat")
print("Preparing regex")
ipRegEx = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
pingsRegEx = re.compile("^([1-9]|[1-9][0])$")
print("Ready")

#workers = (2 * os.cpu_count()) + 1
app.run(host="localhost", port=8000, server='gunicorn')