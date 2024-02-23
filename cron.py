#!/usr/bin/python3
import pymysql.cursors ,json, time, os

fullPath = os.path.realpath(__file__).replace("cron.py","")

print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)

#open a mysql connection
connection = pymysql.connect(host=config['mysql']['host'],user=config['mysql']['user'],password=config['mysql']['password'],database=config['mysql']['database'],cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()
#TIME UWU
current = int(time.time())
#PURGE
cursor.execute("DELETE FROM requests WHERE expiry <= %s",(current,))
#EXECUTE
connection.commit()
#disconnect
connection.close()