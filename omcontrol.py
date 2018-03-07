#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/3/2 11:36
# @Author  : CKHo
# @Email   : ckhoidea@hotmail.com
# @File    : omcontrol.py
# @Software: PyCharm

from stockclib.omServ import mongo_auth_assistant, generate_logger
from configparser import ConfigParser
from datetime import datetime
from time import sleep
import logging

CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
COLL_SECTION = 'Collections'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)


db = mongo_auth_assistant(cfg.get(DB_SECTION, 'address'),
                          int(cfg.get(DB_SECTION, 'port')),
                          cfg.get(DB_SECTION, 'user'),
                          cfg.get(DB_SECTION, 'passwd'),
                          cfg.get(DB_SECTION, 'database'))[cfg.get(DB_SECTION, 'database')]

collection = cfg.get(COLL_SECTION, 'ordermatch_service_coll')
all_open = db[cfg.get(COLL_SECTION, 'trading_days')].find_one()['open']

service_status_logger = generate_logger('serv_status', 'runtime/omctrl.log', logging.WARNING)

day_key = '%Y-%m-%d'
time_key = '%H:%M:%S'

ms = '09:30:00'
mc = '11:30:00'
afts = '13:00:00'
aftc = '15:00:00'

morning = [datetime.strptime(ms, time_key), datetime.strptime(mc, time_key)]
afternoon = [datetime.strptime(afts, time_key), datetime.strptime(aftc, time_key)]


def change_status(tdb, coll, newst):
    query = tdb[coll].find_one()['status']
    tdb[coll].update_one({'status': query}, {'$set': {'status': newst}})


if __name__ == "__main__":
    # 检查是否为交易日，并且在交易时间内让omserver处于运行状态
    while True:
        date = datetime.today()
        today = date.strftime(day_key)
        now = datetime.strptime((datetime.now().strftime(time_key)), time_key)
        if today in all_open:
            if morning[0] < now < morning[1] or afternoon[0] < now < afternoon[1]:
                change_status(db, collection, 'run')
                service_status_logger.warning('run')
                sleep(20)
            else:
                change_status(db, collection, 'stop')
                service_status_logger.warning('stop')
                sleep(20)
        else:
            change_status(db, collection, 'stop')
            service_status_logger.warning('stop')
            sleep(60)




