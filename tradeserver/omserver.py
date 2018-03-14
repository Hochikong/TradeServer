# -*- coding: utf-8 -*-
# @Time    : 2017/12/7 16:59
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : omserver.py
# @Software: PyCharm

from multiprocessing import Process
from multiprocessing.sharedctypes import Array
from stockclib.omServ import clean_order_for_om, cost_cal_for_om, balance_manager, \
    fetch_profitstat, fetch_others, fetch_signal, compare_when_matching, position_manager, matching_without_waiting, \
    generate_logger
from functools import reduce
import os
import tushare
import logging
import time
# import time


# 用于记录服务运行状态
service_status_logger = generate_logger('serv_status', 'runtime/status.log', logging.WARNING)

# 用于记录交易撮合
matching_history_logger = generate_logger('matching_history', 'runtime/match.log', logging.INFO)


# 辅助函数
def parallel_matching(per_order_with_params):
    """
    使用map的撮合函数
    :param per_order_with_params: 每一张订单和对应的游标和费率参数构成的元组:(order, feeR, taxR, cursors)
    :return:
    """
    per_order = per_order_with_params[0]
    feeR = per_order_with_params[1]
    taxR = per_order_with_params[2]
    cursors = per_order_with_params[3]

    compare_result = compare_when_matching(per_order)
    # print('Waiting for matching: | code: %s, price: %s, ops: %s' % (per_order['code'],
    # compare_result, per_order['ops']))
    if compare_result != 'Wait':
        # 准备写入full_history前的数据清理
        per_order = clean_order_for_om(per_order, compare_result)
        # 更新订单的费用和总值
        per_order = cost_cal_for_om(per_order, feeR, taxR)
        order_id = per_order['order_id']
        # 写入操作记录
        cursors['coll_full_history'].insert_one(per_order)
        # 写入持仓
        position_manager(per_order, cursors['coll_positions'])
        # 修改用户余额
        balance_manager(cursors['coll_traders'], per_order)
        # 删除订单
        cursors['coll_orders'].delete_one({'order_id': order_id})
        # print('status: Done, code: %s, price: %s, ops: %s, user_id: %s' %
        # (per_order['code'], compare_result, per_order['ops'], per_order['user_id']))
        # 记录订单完成信息
        matching_history_logger.info('status: Done, code: %s, price: %s, ops: %s, user_id: %s' %
                                     (per_order['code'],
                                      compare_result,
                                      per_order['ops'],
                                      per_order['user_id']))


def parallel_matching_without_wait(per_order_with_params):
    """
    与parallel_matching的区别在于此函数会调用忽略价格直接成交的撮合函数
    :param per_order_with_params: 每一张订单和对应的游标和费率参数构成的元组:(order, feeR, taxR, cursors)
    :return:
    """
    per_order = per_order_with_params[0]
    feeR = per_order_with_params[1]
    taxR = per_order_with_params[2]
    cursors = per_order_with_params[3]

    compare_result = matching_without_waiting(per_order)
    # print('Waiting for matching: | code: %s, price: %s, ops: %s' % (per_order['code'],
    # compare_result, per_order['ops']))
    # 准备写入full_history前的数据清理
    per_order = clean_order_for_om(per_order, compare_result)
    # 更新订单的费用和总值
    per_order = cost_cal_for_om(per_order, feeR, taxR)
    order_id = per_order['order_id']
    # 写入操作记录
    cursors['coll_full_history'].insert_one(per_order)
    # 写入持仓
    position_manager(per_order, cursors['coll_positions'])
    # 修改用户余额
    balance_manager(cursors['coll_traders'], per_order)
    # 删除订单
    cursors['coll_orders'].delete_one({'order_id': order_id})
    # print('status: Done, code: %s, price: %s, ops: %s, user_id: %s' %
    # (per_order['code'], compare_result, per_order['ops'], per_order['user_id']))
    # 记录订单完成信息
    matching_history_logger.info('status: Done, code: %s, price: %s, ops: %s, user_id: %s' %
                                 (per_order['code'],
                                  compare_result,
                                  per_order['ops'],
                                  per_order['user_id']))


# -----------------------------
# 进程函数


def check_status(self_status, address, port, username, passwd, target_db, service_signal):
    signal = fetch_signal(address, port, username, passwd, target_db, service_signal)
    while True:
        status = signal.find_one()['status']
        if bytes.decode(self_status.value) == status:
            pass
        else:
            self_status.value = str.encode(status)
            # print('Current signal status: ', status)
            # 记录服务状态变更
            service_status_logger.warning('Current status: %s' % status)
        time.sleep(5)


def matching(self_status, address, port, username, passwd, target_db, order,
             full_history, positions, trans_history, traders, feeR, taxR, matching_mechanism):   # 还没考虑到撤单
    cursors = fetch_others(address, port, username, passwd, target_db,
                           order, full_history, positions, trans_history, traders)
    while True:
        if bytes.decode(self_status.value) == 'run':
            all_orders = list(cursors['coll_orders'].find())
            all_orders_with_params = [(order, feeR, taxR, cursors) for order in all_orders]
            if matching_mechanism == 'no':
                r = list(map(parallel_matching_without_wait, all_orders_with_params))
            else:
                # 默认均使用等待版撮合函数
                r = list(map(parallel_matching, all_orders_with_params))
            time.sleep(3)
        else:
            # 不处理撮合
            # print('status: stop')
            # 记录等待状态
            matching_history_logger.info('Waiting for orders')
            time.sleep(10)


def profit_statistics(self_status, address, port, username, passwd, target_db, traders, positions, profitstat):
    cursors = fetch_profitstat(address, port, username, passwd, target_db, traders, positions, profitstat)
    while True:
        if bytes.decode(self_status.value) == 'run':
            stats = []
            # 持仓用户的计算方法：持仓股票现市值之和加余额除本金
            all_users = list(cursors['coll_traders'].find())
            all_positions = list(cursors['coll_positions'].find())

            # 无持仓用户计算方法： 余额与本金差值除本金
            all_user_with_positions = [p['user_id'] for p in all_positions if len(p['position']) > 0]  # ['user_id','user_id']
            all_user_without_positions = [u for u in all_users if u['user_id'] not in all_user_with_positions]

            if len(all_user_without_positions) > 0:
                for u in all_user_without_positions:
                    u_balance = float(u['balance'])
                    u_total = float(u['total'])
                    u_AllrateR = round((u_balance - u_total) / u_total, 3)
                    stats.append({'user_id': u['user_id'], 'stat': [{
                        'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        'balance': str(u_balance),
                        'AllrateR': str(u_AllrateR)}]})
            else:
                pass

            # 计算持仓用户的收益
            # 提取余额与本金
            if len(all_user_with_positions) > 0:
                all_user_total_balance = []  # [['total', 'balance'], ['total', 'balance']]
                for user_id in all_user_with_positions:
                    for info in all_users:
                        if user_id in list(info.values()):
                            all_user_total_balance.append(
                                {'user_id': user_id, 'data': [info['total'], info['balance']]})
                # 提取代码、用户id、均价和数量
                all_code_avgprice_amount = []
                for u in all_positions:
                    for p in u['position']:
                        data = {'user_id': u['user_id'], 'caa': (p['code'], p['avgprice'], p['amount'])}
                        all_code_avgprice_amount.append(data)
                # 更新现价
                for i in all_code_avgprice_amount:
                    code = i['caa'][0]
                    i['now_price'] = tushare.get_realtime_quotes(code)['price'][0]
                # 计算现市值
                for i in all_code_avgprice_amount:
                    now_total = int(i['caa'][2]) * float(i['now_price'])
                    i['s_now_total'] = round(now_total, 2)
                # 加上余额求差值
                for user_id in all_user_with_positions:
                    user_id_total = [i['s_now_total'] for i in all_code_avgprice_amount if user_id in list(i.values())]
                    user_id_total = reduce(lambda x, y: x + y, user_id_total)
                    # 用户股票总市值加上余额
                    user_id_now_balance = \
                        [float(i['data'][1]) for i in all_user_total_balance if user_id in list(i.values())][0]
                    user_id_a_total = user_id_now_balance + user_id_total
                    # 本金
                    user_id_origin_total = [float(i['data'][0]) for i in all_user_total_balance
                                            if user_id in list(i.values())][0]
                    # 算收益率
                    AllrateR = round((user_id_a_total - user_id_origin_total) / user_id_origin_total, 3)
                    stat = {'user_id': user_id, 'stat': [{'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                          'balance': str(user_id_now_balance),
                                                          'AllrateR': str(AllrateR)}]}
                    stats.append(stat)
            else:
                pass

            # 写入数据库
            if len(stats) > 0:
                for i in stats:
                    query = cursors['coll_profitstat'].find_one({'user_id': i['user_id']})
                    if query:
                        old_stat = query['stat']
                        old_stat.append(i['stat'][0])
                        cursors['coll_profitstat'].update_one({'user_id': i['user_id']}, {'$set': {'stat': old_stat}})
                    # 无此用户记录时
                    else:
                        cursors['coll_profitstat'].insert_one(i)
            else:
                pass

            time.sleep(21600)  # 每6小时统计一次
        else:
            time.sleep(1800)   # 每半小时再检查信号


class Server(object):
    def __init__(self, address, port, username, passwd, target_db, order, full_history,
                 positions, trans_history, signal, traders, profitstat, feeR, taxR, matching_mechanism):
        self.status = Array('c', b'halt')
        self.address = address
        self.port = port
        self.username = username
        self.passwd = passwd
        self.target_db = target_db
        self.order = order
        self.full_history = full_history
        self.positions = positions
        self.trans_history = trans_history
        self.signal = signal
        self.traders = traders
        self.profitstat = profitstat
        self.feeR = feeR
        self.taxR = taxR
        self.matching_mechanism = matching_mechanism

    def start(self):
        file = open('runtime/omserv_pid', 'w')
        file.write(str(os.getpid()))
        file.close()
        # print('Staring: ', self.status.value)
        # 记录服务启动
        service_status_logger.warning('Service is running')
        checkdb = Process(target=check_status, args=(self.status, self.address,
                                                     self.port, self.username,
                                                     self.passwd, self.target_db, self.signal),
                          name='checkdb')
        matchingserv = Process(target=matching, args=(self.status, self.address,
                                                      self.port, self.username,
                                                      self.passwd, self.target_db,
                                                      self.order, self.full_history,
                                                      self.positions, self.trans_history, self.traders,
                                                      self.feeR, self.taxR, self.matching_mechanism,
                                                      ),
                               name='matchingserv')
        profitstatserv = Process(target=profit_statistics, args=(self.status, self.address,
                                                                 self.port, self.username,
                                                                 self.passwd, self.target_db,
                                                                 self.traders, self.positions, self.profitstat),
                                 name='profitstatserv')
        profitstatserv.start()
        checkdb.start()
        matchingserv.start()
        profitstatserv.join()
        checkdb.join()
        matchingserv.join()




