# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 20:40
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : maintainctl.py
# @Software: PyCharm

from configparser import ConfigParser
from pubfile import modify_print, generate_and_write, helper_print
import pymongo
import re

# --------------------------------------
# Load config.ini and read configuration
CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)

# ----------------
# regular expression compile
generateuser = re.compile("gen -m \d{1,8}")
checkusers = re.compile("check -a")
exitctl = re.compile("exit")
helper = re.compile("help")

if __name__ == "__main__":
    connection = pymongo.MongoClient(cfg.get(DB_SECTION, 'address'), int(cfg.get(DB_SECTION, 'port')))
    if connection.admin.authenticate(
            cfg.get(DB_SECTION, 'user'),
            cfg.get(DB_SECTION, 'passwd'),
            mechanism='SCRAM-SHA-1',
            source=cfg.get(DB_SECTION, 'database')):
        pass
    else:
        raise Exception('Error configure on user or password! ')
    sysdatabase = connection[cfg.get(DB_SECTION, 'database')]
    collect_traders = sysdatabase['traders']

    while True:
        cmd = input('What to do? ')
        if generateuser.match(cmd):
            generate_and_write(cmd, collect_traders)
        elif checkusers.match(cmd):
            rawdata = list(collect_traders.find())
            modify_print(rawdata)
        elif exitctl.match(cmd):
            break
        elif helper.match(cmd):
            helper_print()
        else:
            print('Wrong command!')


