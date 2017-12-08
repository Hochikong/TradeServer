# -*- coding: utf-8 -*-
# @Time    : 2017/12/7 2:09
# @Author  : Hochikong
# @Email   : hochikong@foxmail.com
# @File    : ordermatchexp.py
# @Software: PyCharm

from multiprocessing import Process
from multiprocessing.sharedctypes import Array
import time, os
from pubfile import mongo_auth_assistant


def checkdb(ostatus):
    c = mongo_auth_assistant('localhost', 27017, 'tradesystem', 'system', 'tradesys')
    db = c.tradesys
    signal = db.ordermatch_service
    while True:
        status = signal.find_one()['status']
        print('method', status)
        if bytes.decode(ostatus.value) == status:
            pass
        else:
            ostatus.value = str.encode(status)
        time.sleep(2)


def printx(ostatus):
    while True:
        if bytes.decode(ostatus.value) == 'run':
            time.sleep(2)
            print('----------------------------------------------------')
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            print('====================================================')
        else:
            time.sleep(2)
            print('Not to run')


class Server(object):
    def __init__(self):
        self.status = Array('c', b'stop')

    def start(self):
        print('before', self.status.value)
        runornot = Process(target=checkdb, args=(self.status,))
        printnum = Process(target=printx, args=(self.status,))
        runornot.start()
        printnum.start()
        runornot.join()
        printnum.join()


if __name__ == "__main__":
    file = open('pid', 'w')
    file.write(str(os.getpid()))
    file.close()
    b = Server()
    b.start()









