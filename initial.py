#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2018/3/6 15:47
# @Author  : CKHo
# @Email   : ckhoidea@hotmail.com
# @File    : initial.py
# @Software: PyCharm

from stockclib.omServ import mongo_auth_assistant
from configparser import ConfigParser

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

if __name__ == "__main__":
    db['ordermatch_service'].insert_one({'status': 'run'})