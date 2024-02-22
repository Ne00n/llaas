#!/usr/bin/python3
import pymysql.cursors ,json, time, os

fullPath = os.path.realpath(__file__).replace("cron.py","")

print("Loading config")
with open(f"{fullPath}configs/api.json") as f: config = json.load(f)

# Connect to the database
connection = pymysql.connect(host=config['mysql']['host'],
                            user=config['mysql']['user'],
                            password=config['mysql']['password'],
                            database=config['mysql']['database'],
                            cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

current = int(time.time())
cursor.execute("DELETE FROM requests WHERE expiry <= %s",(current,))
connection.commit()
connection.close()