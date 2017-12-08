# -*- coding: utf-8 -*-
# @Time    : 2017/12/7 16:59
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : omserver.py
# @Software: PyCharm

from multiprocessing import Process
from multiprocessing.sharedctypes import Array
from stockclib.omServ import clean_order_for_om, cost_cal_for_om, generate_positions, \
    generate_positions_update, return_for_tran_history, balance_manager, \
    fetch_profitstat, fetch_others, fetch_signal,compare_when_matching
from datetime import datetime
from functools import reduce
import time
import tushare


# 辅助函数

def position_manager(per_order, positions):
    user_id = per_order['user_id']
    if per_order['ops'] == 'bid':
        data = generate_positions(per_order)
        # 检查用户是否存在position表中
        query_result = positions.find_one({'user_id': user_id})
        # 如果已存在
        if query_result:
            user_position = query_result['position']
            # 检查是否已经持有该股票
            codes = [p['code'] for p in user_position]
            # 增持
            if per_order['code'] in codes:
                # 计算增持时total等数据的新变化
                code_index = codes.index(per_order['code'])
                data_update = generate_positions_update(code_index, per_order, user_position)
                # 把更新应用到原数据持仓信息里
                for k in list(data_update.keys()):
                    user_position[code_index][k] = data_update[k]
                # 更新数据库
                positions.update_one({'user_id': user_id}, {'$set': {'position': user_position}})
                return return_for_tran_history(user_id, per_order, data)
            else:
                # 非增持的情况
                user_position.append(data)
                # 更新用户持仓
                positions.update_one({'user_id': user_id}, {'$set': {'position': user_position}})
                return return_for_tran_history(user_id, per_order, data)
        else:
            document = {'user_id': user_id, 'position': [data, ]}
            positions.insert_one(document)
            # 用于写入trans_history
            return return_for_tran_history(user_id, per_order, data)
    if per_order['ops'] == 'offer':
        query_result = positions.find_one({'user_id': user_id})
        # 此处不再执行用户是否存在的查询，交给REST接口处理
        position_data = query_result['position']
        # 清除指定记录
        d_index = [position_data.index(d) for d in position_data if d['code'] == per_order['code']][0]
        position_data.pop(d_index)
        # 重新写入数据库
        positions.update_one({'user_id': user_id}, {'$set': {'position': position_data}})
        # 更新trans_history
        return {'end': time.strftime("%Y-%m-%d", time.localtime()),
                'code': per_order['code'],
                'user_id': user_id,
                'current_price': tushare.get_realtime_quotes(per_order['code'])['price'][0]}


def transhistory_manager(trans_history, pm_return):
    # 结算更新
    # 卖出结算
    if len(pm_return) == 4:
        user_id = pm_return['user_id']
        code = pm_return['code']
        query_result = trans_history.find_one({'user_id': user_id})
        history = query_result['history']
        # 买入时写入的不含end的数据
        data = [d for d in history if 'end' not in list(d.keys()) and code in list(d.values())][0]
        data_index = history.index(data)
        # 计算损益
        the_return = round((float(pm_return['current_price'])-float(data['avgprice']))*int(data['amount'])
                           -float(data['cost']), 2)
        return_rate = round((the_return/float(data['total'])), 2)
        # 计算日期
        str_now_1 = pm_return['end'].split('-')
        str_ago_2 = data['start'].split('-')
        str_to_int_now = [int(ele) for ele in str_now_1]
        str_to_int_ago = [int(ele) for ele in str_ago_2]
        now = datetime(str_to_int_now[0], str_to_int_now[1], str_to_int_now[2])
        ago = datetime(str_to_int_ago[0], str_to_int_ago[1], str_to_int_ago[2])
        delta = (now-ago).days
        # 补充数据
        data['end'] = pm_return['end']
        data['the_return'] = str(the_return)
        data['rateofR'] = str(return_rate)
        data['during'] = str(delta)
        history[data_index] = data
        # 写入数据库
        trans_history.update_one({'user_id': user_id}, {'$set': {'history': history}})
    # 买入结算
    if len(pm_return) == 2:
        user_id = pm_return['user_id']
        query_result = trans_history.find_one({'user_id': user_id})
        # 如果用户已存在
        if query_result:
            history = query_result['history']
            history.append(pm_return['history'][0])
            trans_history.update_one({'user_id': user_id}, {'$set': {'history': history}})
        else:
            trans_history.insert_one(pm_return)

# -----------------------------
# 进程函数


def check_status(self_status, address, port, username, passwd, target_db, service_signal):
    signal = fetch_signal(address, port, username, passwd, target_db, service_signal)
    while True:
        status = signal.find_one()['status']
        print('status', status)
        if bytes.decode(self_status.value) == status:
            pass
        else:
            self_status.value = str.encode(status)
        time.sleep(5)


def matching(self_status, address, port, username, passwd, target_db, order,
             full_history, positions, trans_history, traders, feeR, taxR):   # 还没考虑到撤单
    cursors = fetch_others(address, port, username, passwd, target_db,
                           order, full_history, positions, trans_history, traders)
    while True:
        if bytes.decode(self_status.value) == 'run':
            all_orders = list(cursors['coll_orders'].find())
            for per_order in all_orders:
                compare_result = compare_when_matching(per_order)
                print('matching: | code: %s, price: %s, ops: %s' % (per_order['code'], compare_result, per_order['ops']))
                if compare_result != 'Wait':
                    # 准备写入full_history前的数据清理
                    per_order = clean_order_for_om(per_order, compare_result)
                    # 更新订单的费用和总值
                    per_order = cost_cal_for_om(per_order, feeR, taxR)
                    order_id = per_order['order_id']
                    # 写入操作记录
                    cursors['coll_full_history'].insert_one(per_order)
                    # 写入持仓
                    result = position_manager(per_order, cursors['coll_positions'])
                    # 修改用户余额
                    balance_manager(cursors['coll_traders'], per_order)
                    # 写入trans_history
                    transhistory_manager(cursors['coll_trans_history'], result)
                    # 删除订单
                    cursors['coll_orders'].delete_one({'order_id': order_id})
                    time.sleep(2)
                else:
                    print('status: waiting for matching')
        else:
            # 不处理撮合
            print('status: stop')
            time.sleep(5)


def profit_statistics(self_status, address, port, username, passwd, target_db, traders, positions, profitstat):
    cursors = fetch_profitstat(address, port, username, passwd, target_db, traders, positions, profitstat)
    while True:
        if bytes.decode(self_status.value) == 'run':
            stats = []
            # 持仓用户的计算方法：持仓股票现市值之和加余额除本金
            all_users = list(cursors['coll_traders'].find())
            all_positions = list(cursors['coll_positions'].find())
            # 无持仓用户计算方法： 余额与本金差值除本金
            all_user_with_positions = [p['user_id'] for p in all_positions]  # ['user_id','user_id']
            all_user_without_positions = [u for u in all_users if u['user_id'] not in all_user_with_positions]
            for u in all_user_without_positions:
                u_balance = float(u['balance'])
                u_total = float(u['total'])
                u_AllrateR = round((u_balance-u_total)/u_total, 3)
                stats.append({'user_id': u['user_id'], 'stat': [{
                    'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    'balance': str(u_balance),
                    'AllrateR': str(u_AllrateR)}]})
            # 计算持仓用户的收益
            # 提取余额与本金
            all_user_total_balance = []   # [['total', 'balance'], ['total', 'balance']]
            for user_id in all_user_with_positions:
                for info in all_users:
                    if user_id in list(info.values()):
                        all_user_total_balance.append({'user_id': user_id, 'data': [info['total'], info['balance']]})
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
                now_total = int(i['caa'][2])*float(i['now_price'])
                i['s_now_total'] = round(now_total, 2)
            # 加上余额求差值
            for user_id in all_user_with_positions:
                user_id_total = [i['s_now_total'] for i in all_code_avgprice_amount if user_id in list(i.values())]
                user_id_total = reduce(lambda x, y: x + y, user_id_total)
                # 用户股票总市值加上余额
                user_id_now_balance = [float(i['data'][1]) for i in all_user_total_balance if user_id in list(i.values())][0]
                user_id_a_total = user_id_now_balance + user_id_total
                # 本金
                user_id_origin_total = [float(i['data'][0]) for i in all_user_total_balance
                                        if user_id in list(i.values())][0]
                # 算收益率
                AllrateR = round((user_id_a_total-user_id_origin_total)/user_id_origin_total, 3)
                stat = {'user_id': user_id, 'stat': [{'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                      'balance': str(user_id_now_balance),
                                                      'AllrateR': str(AllrateR)}]}
                stats.append(stat)

            # 写入数据库
            for i in stats:
                query = cursors['coll_profitstat'].find_one({'user_id': i['user_id']})
                if query:
                    old_stat = query['stat']
                    old_stat.append(i['stat'][0])
                    cursors['coll_profitstat'].update_one({'user_id': i['user_id']}, {'$set': {'stat': old_stat}})
                # 无此用户记录时
                else:
                    cursors['coll_profitstat'].insert_one(i)
            time.sleep(21600)  # 每6小时统计一次
        else:
            time.sleep(1800)   # 每半小时再检查信号


class Server(object):
    def __init__(self, address, port, username, passwd, target_db, order, full_history,
                 positions, trans_history, signal, traders, profitstat, feeR, taxR):
        self.status = Array('c', b'stop')
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

    def start(self):
        print('before', self.status.value)
        checkdb = Process(target=check_status, args=(self.status, self.address,
                                                     self.port, self.username,
                                                     self.passwd, self.target_db, self.signal))
        matchingserv = Process(target=matching, args=(self.status, self.address,
                                                      self.port, self.username,
                                                      self.passwd, self.target_db,
                                                      self.order, self.full_history,
                                                      self.positions, self.trans_history, self.traders,
                                                      self.feeR, self.taxR,
                                                      ))
        profitstatserv = Process(target=profit_statistics, args=(self.status, self.address,
                                                                 self.port, self.username,
                                                                 self.passwd, self.target_db,
                                                                 self.traders, self.positions, self.profitstat))
        checkdb.start()
        matchingserv.start()
        profitstatserv.start()
        checkdb.join()
        matchingserv.join()
        profitstatserv.join()



