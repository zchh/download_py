
import requests
import sys
import io
import PIL.Image as image
import time,re, random
import mysql.connector
import redis
import json
import flask
import threading
import asyncio

from aiohttp import web

from multiprocessing import Process
from flask import request,redirect,url_for #想获取到请求参数的话，就得用这个
# from pyvirtualdisplay import Display #linux
server = flask.Flask(__name__) #把这个python文件当做一个web服务

from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support.ui import Select

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops


# browser = webdriver.Chrome()
# conn = mysql.connector.connect(user='root', password='', database='material_download')
# cursor = conn.cursor()

def main():
    conn = mysql.connector.connect(user='root', password='', database='material_download')
    cursor = conn.cursor()


    # cursor.execute('select * from cookie')
    # account_values = cursor.fetchall()
    # print(account_values)

    cursor.execute('UPDATE cookie SET cookie_value=%s,cookie_is_valid=%s WHERE cookie_account_id=%s', ('abcc', 1, 5))
    conn.commit()
    print('xx')

if __name__ == "__main__":
    pass
    main()
