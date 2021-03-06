# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 14:33
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : tserver.py
# @Software: PyCharm

from tradeserver import app
from flask import request, jsonify, render_template, session, Response
from configparser import ConfigParser
from stockclib.omServ import json_to_dict, token_certify, check_orders, \
    mongo_auth_assistant, clean_order, real_time_profit_statistics, generate_fhist_csv
from pyecharts import Line

# --------------------------------------
# Load config.ini and read configuration
CONFIG_FILE = 'config.ini'
DB_SECTION = 'DB'
TRADE_SECTION = 'Trade'
COLL_SECTION = 'Collections'
cfg = ConfigParser()
cfg.read(CONFIG_FILE)


# ------------------
# Connect to MongoDB
connection = mongo_auth_assistant(cfg.get(DB_SECTION, 'address'),
                                  int(cfg.get(DB_SECTION, 'port')),
                                  cfg.get(DB_SECTION, 'user'),
                                  cfg.get(DB_SECTION, 'passwd'),
                                  cfg.get(DB_SECTION, 'database'))
sysdatabase = connection[cfg.get(DB_SECTION, 'database')]
collect_traders = sysdatabase[cfg.get(COLL_SECTION, 'traders_coll')]
collect_orders = sysdatabase[cfg.get(COLL_SECTION, 'orders_coll')]
collect_full_history = sysdatabase[cfg.get(COLL_SECTION, 'full_history_coll')]
collect_positions = sysdatabase[cfg.get(COLL_SECTION, 'positions_coll')]
collect_trans_history = sysdatabase[cfg.get(COLL_SECTION, 'trans_history_coll')]
collect_profitstat = sysdatabase[cfg.get(COLL_SECTION, 'profitstat_coll')]


# ---------------------------------
# REST API for trader
app.secret_key = 'AeuOSOD84:324/]DFA@3XX,DLdxcEWKKw#@cvccyazm'


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
                order_data = collect_orders.find_one({'order_id': jdict['order_id']})
                if order_data:
                    order_after_clean = clean_order(order_data)
                    # 分别写入操作记录和删除被撤订单
                    collect_full_history.insert_one(order_after_clean)
                    delete_obj = collect_orders.delete_one({'order_id': jdict['order_id']})
                    if delete_obj.deleted_count > 0:
                        return jsonify({'status': 'Done', 'msg': 'Order cancel'})
                    else:
                        return jsonify({'status': 'Error', 'msg': 'No such order'})
                else:
                    return jsonify({'status': 'Error', 'msg': 'No such order'})
            # 买入或者卖出的撤单
            else:
                # 根据ops进行操作，买入、卖出
                # 先检查是否能进入撮合系统
                positions = collect_positions.find_one({'user_id': authentication_result['user_id']})
                check_result = check_orders(jdict, authentication_result,
                                            float(cfg.get(TRADE_SECTION, 'taxrate')),
                                            float(cfg.get(TRADE_SECTION, 'feerate')),
                                            positions)
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


@app.route('/user', methods=['POST'])
def return_user_info():
    """
    根据用户的请求返回指定的数据
    请求：
    trade_token放在头部
    请求体： {'query': 'positions/full_history/trans_history/profitstat/user/real_time_profit'}
    :return:  {'user_id','what you want'}
    """
    jdict = json_to_dict(request.data)
    authentication_result = token_certify(collect_traders, request.headers)
    if 'Error' in list(authentication_result.values()):
        return jsonify(authentication_result)
    else:
        # 通过认证
        user_id = authentication_result['user_id']
        if jdict['query'] == 'positions':
            query = collect_positions.find_one({'user_id': user_id})
            if query:
                query.pop('_id')
                return jsonify(query)
            else:
                return jsonify({'status': 'Error', 'msg': 'No any position'})
        elif jdict['query'] == 'full_history':
            query = list(collect_full_history.find({'user_id': user_id}))
            if query:
                for q in query:
                    q.pop('_id')
                    q.pop('user_id')
                return jsonify({'user_id': user_id, 'full_history': query})
            else:
                return jsonify({'status': 'Error', 'msg': 'No any operation history'})
        elif jdict['query'] == 'profitstat':
            query = collect_profitstat.find_one({'user_id': user_id})
            if query:
                query.pop('_id')
                return jsonify(query)
            else:
                return jsonify({'status': 'Error', 'msg': 'No any profit statistics record'})
        elif jdict['query'] == 'user':
            query = collect_traders.find_one({'user_id': user_id})
            if query:
                query.pop('_id')
                query.pop('token')
                return jsonify(query)
            else:
                jsonify({'status': 'Error', 'msg': 'You meet a crazy bug'})
        elif jdict['query'] == 'real_time_profit':
            stat = real_time_profit_statistics(collect_traders, collect_positions)
            belong_to_user = [st for st in stat if user_id in list(st.values())]
            return jsonify(belong_to_user)
        else:
            return jsonify({'status': 'Error', 'msg': 'Wrong query'})


# ---------------------------------------------
# REST for monitor

@app.route('/', methods=['GET'])
# PC版页面
def print_login_page():
    return render_template("login.html")


@app.route('/mlogin', methods=['GET'])
# 移动版页面
def show_mlogin():
    return render_template("mlogin.html")


@app.route('/mmo', methods=['GET'])
def show_mmo():
    return render_template("/mmonitor.html")


@app.route('/validate', methods=['POST'])
# 登陆验证
def check_trade_token():
    jdict = json_to_dict(request.data)
    all_user = list(collect_traders.find())
    tokens = []
    for u in all_user:
        tokens.append(u['token'])

    if jdict['token'] in tokens:
        session['token'] = jdict['token']
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error'})


@app.route('/monitor', methods=['GET'])
# 渲染monitor
def print_monitor_page():
    token = session['token']
    all_user = list(collect_traders.find())
    user_id = [ur['user_id'] for ur in all_user if ur['token'] == token][0]
    return render_template("monitor.html", myechart=profitstat_chart(user_id))


@app.route('/logout', methods=['POST'])
# 注销验证
def logout():
    jdict = json_to_dict(request.data)
    if jdict['msg'] == 'logout':
        session.pop('username', None)
        return jsonify({'msg': 'ok'})
    else:
        return jsonify({'msg': 'ok'})


@app.route('/fhist.csv', methods=['GET'])
# 返回csv文件留
def download():
    token = session['token']
    return Response(generate_fhist_csv(token, collect_traders, collect_full_history), mimetype='text/csv')

# ---------------------------------------------
# 异常状态处理


@app.errorhandler(404)  # 处理404的问题
def not_found(e):
    return render_template("page_not_found.html")


@app.errorhandler(405)  # 处理不允许的HTTP谓词
def ban_method(e):
    return render_template("you_cant_use_this_method.html")


# ---------------------------------------------
# 图表展示函数，未来需要迁入omServ


def profitstat_chart(user_id):
    query = list(collect_profitstat.find())
    user_profithist = [data for data in query if data['user_id'] == user_id][0]['stat']

    # 创建图表
    line = Line("您的收益变化")
    attrs = [i['date'] for i in user_profithist]
    x_dates = [i.split(' ')[0] for i in attrs]
    y_profit = [i['AllrateR'] for i in user_profithist]
    line.add("总收益", x_dates, y_profit, is_label_show=True, is_datazoom_show=True,
             mark_point=['average'], is_more_utils=True)
    return line.render_embed()


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


