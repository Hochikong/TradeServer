# -*- coding: utf-8 -*-
# @Time    : 2017/12/8 2:13
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : omrun.py
# @Software: PyCharm

from tradeserver.omserver import Server
from configparser import ConfigParser

CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
TRADE_SECTION = 'Trade'
COLL_SECTION = 'Collections'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)

if __name__ == "__main__":
    s = Server(cfg.get(DB_SECTION, 'address'),
               int(cfg.get(DB_SECTION, 'port')),
               cfg.get(DB_SECTION, 'user'),
               cfg.get(DB_SECTION, 'passwd'),
               cfg.get(DB_SECTION, 'database'),
               cfg.get(COLL_SECTION, 'orders_coll'),
               cfg.get(COLL_SECTION, 'full_history_coll'),
               cfg.get(COLL_SECTION, 'positions_coll'),
               cfg.get(COLL_SECTION, 'trans_history_coll'),
               cfg.get(COLL_SECTION, 'ordermatch_service_coll'),
               cfg.get(COLL_SECTION, 'traders_coll'),
               cfg.get(COLL_SECTION, 'profitstat_coll'),
               float(cfg.get(TRADE_SECTION, 'taxrate')),
               float(cfg.get(TRADE_SECTION, 'feerate')))
    s.start()

