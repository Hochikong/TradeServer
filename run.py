# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 14:39
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : run.py
# @Software: PyCharm

from tradeserver import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)
