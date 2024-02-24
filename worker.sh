#!/bin/bash
if [[ $(id -u) -ne 0 ]] ; then echo "Please run as root" ; exit 1 ; fi
apt-get install python3 python3-requests fping git cron -y
cd /home/
git clone https://github.com/Ne00n/llaas.git
cd llaas
cp configs/worker.example.json configs/worker.json
useradd llaas -r -d /home/llaas -s /bin/bash
chown -R llaas:llaas /home/llaas/
cp configs/llaasWorker.service /etc/systemd/system
systemctl enable llaasWorker && systemctl start llaasWorker