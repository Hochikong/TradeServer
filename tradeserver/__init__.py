# -*- coding: utf-8 -*-
# @Time    : 2017/12/2 14:32
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : __init__.py
# @Software: PyCharm

from flask import Flask
app = Flask(__name__)

from tradeserver import tserver


