#!/usr/bin/python3
from bottle import HTTPResponse, route, run, request, template
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import threading, json, re

requests = {}
mutex = threading.Lock()

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
        if not ipv4[0] in requests: 
            mutex.acquire()
            requests[ipv4[0]] = {"status":"accepted","location":{"continent":""}}
            mutex.release()
        return HTTPResponse(status=200, body=requests[ipv4[0]])
    else:
        return HTTPResponse(status=400, body={"data":"no valid IPv4"})

print("Loading config")
with open('api.json') as f: config = json.load(f)
print("Ready")

run(host="::", port=8080, server='paste')