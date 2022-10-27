# -*- coding = utf-8 -*-
# @Time : 2021-01-10 20:42
# @Author : Danny
# @File : simultaneous_run.py
# @Software: PyCharm
import os
import threading
import time
from pynput.keyboard import Key, Listener, Controller,Events


def run_file(file):
    os.system("python main.py --node " + file)


if __name__ == '__main__':
    # files = ["./u_main.py", "./v_main.py", "./w_main.py", "./x_main.py", "./y_main.py", "./z_main.py", "r_main.py",
    #          "s_main.py", "t_main.py"]
    # files = ["./w_main.py", "./x_main.py"]
    # files = ["./w_main.py", "./u_main.py"]
    # files = ["./u_main.py", "./v_main.py"]
    # files = ["u_main.py", "x_main.py"]
    # files = ["v_main.py", "x_main.py"]
    files = ["u","v","w"]
    for file in files:
        bellman = threading.Thread(target=run_file, args=(file,))
        bellman.start()


# TODO:
# - show network อย่างเดียว ซ่อน router
# - เปลี่ยน format print 
# - เพิ่ม - ลบ router จาก array neighbour_addr
# - 