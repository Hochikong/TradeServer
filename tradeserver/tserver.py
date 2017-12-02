# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 14:33
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : tserver.py
# @Software: PyCharm

from tradeserver import app
from flask import render_template, request, json, jsonify, session, abort
from configparser import ConfigParser
import pymongo


# --------------------------------------
# Load config.ini and read configuration
CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)


# ------------------
# Connect to MongoDB
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
collect_orders = sysdatabase['orders']
# collect_transaction_history = database['trans_history']
# collect_transaction_full_history = database['full_history']
# collect_position = database['position']


# ---------------------------------
# REST API for trader


@app.route('/order', methods=['POST', 'GET'])
def takeorder():
    """
    Requests style:{}
    :return:
    """
    if request.method == 'POST':
        jsonstr = request.data
        jsondict = json.loads(jsonstr, encoding='utf-8')
        print(jsondict)
        return jsonify({'MESSAGE': 'hello'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


