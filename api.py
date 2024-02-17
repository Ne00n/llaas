#!/usr/bin/python3
import pymysql.cursors ,json, pyasn, time, re, os
from socketify import App

fullPath = os.path.realpath(__file__).replace("api.py","")
app = App()

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user='llaas',
                             password='llaas',
                             database='llaas',
                             cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

def validate(payload):
    if not "token" in payload or not "worker" in payload: return False
    if not re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL): return False
    if not re.findall(r"^([A-Za-z0-9.=+-]{3,50})$",payload['worker'],re.MULTILINE | re.DOTALL): return False
    for worker,details in config['workers'].items():
        if worker == payload['worker'] and details['token'] == payload['token']: return True

def insert(subnet,ip,pings):
    expiry = int(time.time()) + 1800
    cursor.execute(f"INSERT INTO requests (subnet, ip, expiry) VALUES (%s,%s,%s)",(subnet,ip, expiry))
    for worker,details in config['workers'].items():
        for run in range(int(pings)): cursor.execute(f"INSERT INTO results (subnet, worker) VALUES (%s,%s)",(subnet, worker))
    connection.commit()

def cleanUp(subnet):
    cursor.execute(f"DELETE FROM requests WHERE subnet = %s",(subnet,))
    connection.commit()

def query(res,request,pings):
    if len(request) > 100: 
        res.write_status(413)
        res.send("Way to fucking long.")
    request = request.replace("/","")
    ipv4 = ipRegEx.findall(request)
    if not ipv4: 
        res.write_status(400)
        res.send("Invalid IPv4 address.")
    result = pingsRegEx.findall(pings)
    if not result: 
        res.write_status(400)
        res.send("Invalid Amount of Pings.")
    asndata = asndb.lookup(ipv4[0])
    if asndata[0] is None: 
        res.write_status(404)
        res.send("Unable to lookup IPv4 address.")
        return
    cursor.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency,requests.expiry FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet = %s ORDER BY results.ID",(asndata[1],))
    connection.commit()
    response = list(cursor)
    if response and int(time.time()) > int(response[0]['expiry']):
        cleanUp(asndata[1])
        response = {}
    if not response:
        insert(asndata[1],ipv4[0],pings)
        res.write_status(200)
        res.send({"subnet":asndata[1],"ip":ipv4[0],"data":{}})
    else:
        data = {}
        for row in response:
            if not row['worker'] in data: data[row['worker']] = []
            if row['latency'] == None:
               data[row['worker']].append(0)
            else: 
                data[row['worker']].append(int(row['latency']))
        res.write_status(200)
        res.send({"subnet":asndata[1],"ip":ipv4[0],"data":data})

async def jobGet(res, req):
    payload = await res.get_json()
    if not validate(payload): 
        res.write_status(413)
        res.send("Invalid Auth.")
    cursor.execute("SELECT results.ID,requests.subnet,requests.ip,results.worker FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE results.worker = %s AND results.latency is NULL GROUP BY requests.subnet LIMIT 1000",(payload['worker'],))
    ips = list(cursor)
    res.write_status(200)
    res.send({"ips":ips})
app.post('/job/get',jobGet)

async def jobDeliver(res, req):
    payload = await res.get_json()
    if not validate(payload):
        res.write_status(413)
        res.send("Invalid Auth.")
    for subnet,details in payload['data'].items():
        cursor.execute(f"UPDATE results SET latency = %s WHERE subnet = %s and worker = %s and ID = %s",(details['latency'],subnet,payload['worker'],details['id'],))
    connection.commit()
    res.write_status(200)
    res.send({})
app.post('/job/deliver',jobDeliver)

async def pingMulti(res, req):
    return query(res,req.get_parameter(0),req.get_parameter(1))
app.get("/:request/:pings",pingMulti)

async def ping(res, req):
    return query(res,req.get_parameter(0),"1")
app.get("/:request",ping)

app.any("/*", lambda res,req: res.write_status(404).end("Not Found"))

print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn(f"{fullPath}asn.dat")
print("Preparing regex")
ipRegEx = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
pingsRegEx = re.compile("^([1-9]|[1-9][0])$")
print("Ready")

app.listen(8888, lambda config: print("Listening on port http://localhost:%d now\n" % config.port))
app.run()