# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 21:03
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : pubfile.py
# @Software: PyCharm

import random
import string


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
    userid = generate_random_str(8)
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
