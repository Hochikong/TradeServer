# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 14:33
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : tserver.py
# @Software: PyCharm

from tradeserver import app
from flask import render_template, request, json, jsonify, session, abort
from configparser import ConfigParser
from pubfile import json_to_dict, token_certify, check_orders, mongo_auth_assistant
import pymongo

# --------------------------------------
# Load config.ini and read configuration
CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
TRADE_SECTION = 'Trade'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)


# ------------------
# Connect to MongoDB
connection = mongo_auth_assistant(cfg.get(DB_SECTION, 'address'),
                                  int(cfg.get(DB_SECTION, 'port')),
                                  cfg.get(DB_SECTION, 'user'),
                                  cfg.get(DB_SECTION, 'passwd'),
                                  cfg.get(DB_SECTION, 'database'))
#connection = pymongo.MongoClient(cfg.get(DB_SECTION, 'address'), int(cfg.get(DB_SECTION, 'port')))
#if connection.admin.authenticate(
#    cfg.get(DB_SECTION, 'user'),
#    cfg.get(DB_SECTION, 'passwd'),
#    mechanism='SCRAM-SHA-1',
#    source=cfg.get(DB_SECTION, 'database')):
#    pass
#else:
#    raise Exception('Error configure on user or password! ')
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
    下单请求:{code:str,name:str,ops:str,price:str,amount:str}
    撤单请求:{ops:str,order_id:str}
    需要把token放在请求头部trade_token键
    :return:
    """
    # 处理下单、撤单的交易请求
    if request.method == 'POST':
        jdict = json_to_dict(request.data)  # trade message
        authentication_result = token_certify(collect_traders, request.headers)  # 检查token
        if 'Error' in list(authentication_result.values()):
            return jsonify(authentication_result)
        else:
            # 撤单逻辑
            if 'order_id' in list(jdict.keys()) and jdict['ops'] == 'cancel':
                delete_obj = collect_orders.delete_one({'order_id': jdict['order_id']})
                if delete_obj.deleted_count > 0:
                    return jsonify({'status': 'Done', 'msg': 'Order cancel'})
                else:
                    return jsonify({'status': 'Error', 'msg': 'No such order'})
            # 买入或者卖出的撤单
            else:
                # 根据ops进行操作，买入、卖出
                # 先检查是否能进入撮合系统
                check_result = check_orders(jdict, authentication_result,
                                            float(cfg.get(TRADE_SECTION, 'taxrate')),
                                            float(cfg.get(TRADE_SECTION, 'feerate')))
                if 'Error' in list(check_result.values()):
                    return jsonify(check_result)
                else:
                    collect_orders.insert_one(check_result)
                    return jsonify({'status': 'Done', 'msg': {'order_id': check_result['order_id']}})
    # 查询订单
    if request.method == 'GET':
        authentication_result = token_certify(collect_traders, request.headers)
        if 'Error' in list(authentication_result.values()):
            return jsonify(authentication_result)
        else:
            order_belong_to_user = list(collect_orders.find({'user_id': authentication_result['user_id']}))
            for order in order_belong_to_user:
                order.pop('_id')
            return jsonify({'status': 'Done', 'msg': {'remain_orders': order_belong_to_user}})  # 返回剩余订单


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


