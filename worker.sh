#!/bin/bash
if [[ $(id -u) -ne 0 ]] ; then echo "Please run as root" ; exit 1 ; fi
apt-get install python3 python3-pip fping git cron -y
pip3 install pyasn requests bottle gunicorn
cd /home/
git clone https://github.com/Ne00n/llaas.git
cd llaas
cp configs/worker.example.json configs/worker.json
useradd llaas -r -d /home/llaas -s /bin/bash
chown -R llaas:llaas /home/llaas/
crontab -u llaas -l 2>/dev/null | { cat; echo "* * * * *  python3 /home/llaas/worker.py > /dev/null 2>&1"; } | crontab -u llaas -