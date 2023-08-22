from urllib.parse import urlparse
from threading import Thread
import random, sys
import http.client as httplib
from queue import Queue

concurrent = 200

def doWork():
    while True:
        url = q.get()
        status, url = getStatus(url)
        #doSomethingWithResult(status, url)
        q.task_done()

def getStatus(ourl):
    try:
        url = urlparse(ourl)
        conn = httplib.HTTPConnection(url.netloc)   
        conn.request("HEAD", url.path)
        res = conn.getresponse()
        return res.status, ourl
    except:
        return "error", ourl

def doSomethingWithResult(status, url):
    print(status, url)

q = Queue(concurrent * 2)
for i in range(concurrent):
    t = Thread(target=doWork)
    t.daemon = True
    t.start()
try:
    for run in range(2000):
        ip = ".".join(map(str, (random.randint(0, 255) 
                        for _ in range(4))))
        q.put(f"http://127.0.0.1:8080/{ip}")
    q.join()
except KeyboardInterrupt:
    sys.exit(1)