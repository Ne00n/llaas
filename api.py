from bottle import HTTPResponse, route, run, request, template
import dns.resolver, ipaddress, socket, pyasn, json, os, re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

requests = {}
mutex = threading.Lock()
@route('/job/<token>', method='GET')
def index(token=''):
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL)
    if not token or not token in config['workers']: return HTTPResponse(status=400, body={"error":"Invalid Token"})
    mutex.acquire()
    response = {}
    for ip, request in requests.items():
        if request["status"] == "accepted":
            requests[ip]["status"] = "assigned"
            response = requests[ip]["status"]
            break
    mutex.release()
    return HTTPResponse(status=200, body={response})

@route('/job/<token>', method='POST')
def index(token=''):
    token = re.findall(r"^([A-Za-z0-9/.=+]{30,60})$",payload['token'],re.MULTILINE | re.DOTALL)
    if not token or not token in config['workers']: return HTTPResponse(status=400, body={"error":"Invalid Token"})
    payload = json.load(request.body)
    mutex.acquire()
    ip = list(payload.keys())[0]
    requests[ip] = payload
    mutex.release()
    return HTTPResponse(status=200, body={})

@route('/<request>', method='GET')
def index(request=''):
        if len(request) > 100:
            return HTTPResponse(status=414, body={"data":"way to fucking long"})
        request = request.replace("/","")
        print("request",request)
        ipv4 = re.findall("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",request, re.MULTILINE)
        if ipv4:
            if not ipv4[0] in request: 
                mutex.acquire()
                requests[ipv4[0]] = {"status":"accepted","location":{"continent":""}}
                mutex.release()
            return HTTPResponse(status=200, body=requests[ipv4[0]])
        else:
            return HTTPResponse(status=400, body={"data":"no valid IPv4"})

print("Loading config")
with open('config.json') as f: config = json.load(f)
print("Ready")

run(host="::", port=8080, server='paste')