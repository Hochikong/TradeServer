# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 21:03
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : pubfile.py
# @Software: PyCharm

from flask import json
import uuid
import random
import string
import time
import pymongo


def generate_random_str(length):
    """
    生成一个固定长度的随机字符串
    :param length: 数字长度
    :return: 随机字符串
    """
    rstr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    return rstr


def modify_print(rawdata):
    """
    根据数据库的查询调整输出，主要是调整balance的项
    :param rawdata: 数据库查询的list后的结果
    :return:
    """
    strdata = []
    try:
        maxbalancelength = len(max([r['balance'] for r in rawdata], key=len))
        maxtotallength = len(max([r['total'] for r in rawdata], key=len))
        useforprint = max(maxbalancelength, maxtotallength)
        for row in rawdata:
            strdata.append('| User ID: %s | Token: %s | Total: %s | Balance: %s |'
                           % (row['user_id'],
                              row['token'],
                              row['total']+' '*(useforprint-len(row['total'])),
                              row['balance']+' '*(useforprint-len(row['balance']))))
        maxlength = len(max(strdata, key=len))
    except ValueError:
        print('No more user now')
    else:
        for row in strdata:
            print('-' * maxlength)
            print(row)
            print('-' * maxlength)


def generate_and_write(raw_param, trader_doc):
    """
    生成用户ID和token并记录total和balance
    :param raw_param: 原始终端输入
    :param trader_doc: 制定的数据库文档
    :return:
    """
    total = raw_param.split("-m ")[-1]
    userid = str(uuid.uuid1())
    usertoken = generate_random_str(50)
    trader_doc.insert_one({'user_id': userid, 'token': usertoken, 'total': total, 'balance': total})
    print('User ID: ', userid, '\n')
    print('Token: ', usertoken)


def helper_print():
    """
    打印帮助
    :return:
    """
    print('gen: 生成新用户并返回信息')
    print(' -m  指定账户可用资金量', '\n')
    print('check: 查询用户信息')
    print(' -a  查询所有用户信息', '\n')
    print('exit: 退出工具', '\n')
    print('目前所有可用参数均强制使用')


def json_to_dict(rawdata):
    """
    把request中的json转换为字典
    :param rawdata: request.data
    :return: python dict
    """
    jsonstr = rawdata
    jsondict = json.loads(jsonstr, encoding='utf-8')
    return jsondict


def token_certify(document, header):
    """
    根据传入的headers找到trade_token值并在数据库中查找对应的ID，若存在则返回用户数据，否则返回错误信息
    :param document: traders文档
    :param header: request.headers
    :return: python dict
    """
    query = [x for x in list(document.find()) if header['trade_token'] in list(x.values())]
    if len(query) > 0:
        return query[0]
    else:
        return {'status': 'Error', 'msg': 'No such user'}


def check_orders(jdict, authinfo, taxR, feeR):   # 12.05卖出逻辑尚未完成
    """
    从原始json转化的dict中获取指定的值，防止输入不允许的内容
    :param jdict: 交易请求中的jdict
    :param authinfo: authentication information
    :param taxR: 印花税率，int类型
    :param feeR: 手续费率，int类型，不足5元算5元
    :return: python dict
    """
    try:
        order = {'code': jdict['code'], 'name': jdict['name']}

        # 检查数量是否合规
        if int(jdict['amount']) % 100 == 0:
            order['amount'] = jdict['amount']
        else:
            return {'status': 'Error', 'msg': 'Amount should be multiple of 100'}

        # 计算费用
        if jdict['ops'] == 'bid':
            ordertotal = round(int(order['amount']) * float(jdict['price']), 2)
            ordertax = round(ordertotal*taxR, 2)  # 输入的税率和手续费率默认为float型,使用round截断小数
            orderfee = round(ordertotal*feeR, 2)
            if orderfee < 5:
                orderfee = 5
            if ordertotal+ordertax+orderfee > float(authinfo['balance']):  # balance在traders表上为字符串
                return {'status': 'Error', 'msg': "You don't have enough money"}
            else:
                order['price'] = jdict['price']
                order['total'] = str(ordertotal)
                order['tax'] = str(ordertax)
                order['fee'] = str(orderfee)
                order['cost'] = str(round(ordertax+orderfee, 2))
                order['order_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                order['user_id'] = authinfo['user_id']
                order['ops'] = jdict['ops']
                order['order_id'] = generate_random_str(10)  # 根据ID才能撤单
                return order

        elif jdict['ops'] == 'offer':
            ordertotal = round(int(order['amount']) * float(jdict['price']), 2)
            ordertax = round(ordertotal * taxR, 2)
            orderfee = round(ordertotal * feeR, 2)

            if orderfee < 5:
                orderfee = 5
            order['price'] = jdict['price']
            order['total'] = str(ordertotal)
            order['tax'] = str(ordertax)
            order['fee'] = str(orderfee)
            order['cost'] = str(round(ordertax+orderfee, 2))
            order['order_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            order['user_id'] = authinfo['user_id']
            order['ops'] = jdict['ops']
            order['order_id'] = generate_random_str(10)

            return order
        else:
            return {'status': 'Error', 'msg': "Wrong ops"}

    except KeyError:
        return {'status': 'Error', 'msg': "Invalid input or wrong requests body"}


def mongo_auth_assistant(address, port, username, passwd, database):
    """
    用于简化MongoDB认证
    :param address: ...
    :param port: ...
    :param username: ...
    :param passwd: ...
    :param database: 用户所属数据库
    :return: 连接对象
    """
    connection = pymongo.MongoClient(address, port)
    if connection.admin.authenticate(username, passwd, mechanism='SCRAM-SHA-1', source=database):
        pass
    else:
        raise Exception('Error configure on user or password! ')
    return connection






