#!/usr/bin/python3
import pymysql.cursors ,json, pyasn, time, re, os
from socketify import App

fullPath = os.path.realpath(__file__).replace("api.py","")

print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)
print("Loading pyasn")
asndb = pyasn.pyasn(f"{fullPath}asn.dat")
print("Preparing regex")
ipRegEx = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
pingsRegEx = re.compile("^([1-9]|[1-9][0])$")
print("Ready")

def validate(payload):
    if not "token" in payload or not "worker" in payload: return False
    if not re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL): return False
    if not re.findall(r"^([A-Za-z0-9.=+-]{3,50})$",payload['worker'],re.MULTILINE | re.DOTALL): return False
    for worker,details in config['workers'].items():
        if worker == payload['worker'] and details['token'] == payload['token']: return True

def findSubnet(subnet,dbResult):
    response = []
    for row in dbResult:
        if row['subnet'] == subnet: response.append(row)
    return response

def run(app: App): 
    # Connect to the database
    connection = pymysql.connect(host=config['mysql']['host'],
                                user=config['mysql']['user'],
                                password=config['mysql']['password'],
                                database=config['mysql']['database'],
                                cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()

    def query(res,request,pings):
        if len(request) > 15000: 
            res.write_status(413)
            res.send("Way to fucking long.")
            return
        request = request.replace("/","")
        if "," in request: 
            request = request.split(",")
        else:
            request = [request]
        for ip in request:
            ipv4 = ipRegEx.findall(ip)
            if not ipv4:
                res.write_status(400)
                res.send("Invalid IPv4 address.")
                return
        result = pingsRegEx.findall(pings)
        if not result: 
            res.write_status(400)
            res.send("Invalid Amount of Pings.")
            return
        payload = []
        lookup,commit = {},False
        for ip in request:
            asndata = asndb.lookup(ip)
            if asndata[0] is None: continue
            lookup[asndata[1]] = ip
        format_strings = ','.join(['%s'] * len(lookup))
        cursor.execute("SELECT requests.subnet,requests.ip,results.worker,results.latency,requests.expiry FROM requests LEFT JOIN results ON requests.subnet = results.subnet WHERE requests.subnet IN (%s) ORDER BY results.ID" % format_strings,
                    tuple(list(lookup)))
        connection.commit()
        dbResult = list(cursor)
        for subnet,ip in lookup.items():
            dbRecord = findSubnet(subnet,dbResult)
            if dbRecord and int(time.time()) > int(dbRecord[0]['expiry']):
                cursor.execute(f"DELETE FROM requests WHERE subnet = %s",(dbRecord[0]['subnet'],))
                connection.commit()
                dbRecord = []
            if not dbRecord:
                expiry = int(time.time()) + 1800
                cursor.execute(f"INSERT INTO requests (subnet, ip, expiry) VALUES (%s,%s,%s)",(subnet,ip, expiry))
                commit = True
            data = {}
            for row in dbRecord:
                if not row['worker'] in data: data[row['worker']] = []
                if row['latency'] == None:
                    data[row['worker']].append(0)
                else: 
                    data[row['worker']].append(float(row['latency']))
            payload.append({"subnet":asndata[1],"ip":ip,"results":data})
        if commit: connection.commit()
        res.write_status(200)
        res.send(json.dumps(payload, indent=4))

    async def jobGet(res, req):
        payload = await res.get_json()
        if not validate(payload): 
            res.write_status(413)
            res.send("Invalid Auth.")
        cursor.execute("SELECT results.ID,requests.subnet,requests.ip,results.worker FROM results LEFT JOIN requests ON results.subnet = requests.subnet WHERE results.worker = %s AND results.latency is NULL ORDER BY ID LIMIT 1500;",(payload['worker'],))
        ips = list(cursor)
        res.write_status(200)
        res.send({"ips":ips})
    app.post('/job/get',jobGet)

    async def jobDeliver(res, req):
        payload = await res.get_json()
        if not validate(payload):
            res.write_status(413)
            res.send("Invalid Auth.")
        toInsert = []
        for subnet,details in payload['data'].items(): toInsert.append([details['latency'],subnet,payload['worker'],details['id']])
        cursor.executemany(f"UPDATE results SET latency = %s WHERE subnet = %s and worker = %s and ID = %s",(toInsert))
        connection.commit()
        res.write_status(200)
        res.send({})
    app.post('/job/deliver',jobDeliver)

    async def ping(res, req):
        return query(res,req.get_parameter(0),"1")
    app.get("/:request",ping)