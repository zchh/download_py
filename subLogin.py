
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


#爬虫模拟的浏览器头部信息
agent = 'MMozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0'
headers = {
        "User-Agent": agent
        }


def database():
    conn = mysql.connector.connect(user='root', password='ZC123', database='material_download')
    return conn.cursor()

def login(browser, account, password):
    url = r'https://graph.qq.com/oauth2.0/show?which=Login&display=pc&client_id=100414805&redirect_uri=http%3A%2F%2Fwww.58pic.com%2Findex.php%3Fm%3Dlogin%26a%3Dcallback%26type%3Dqq&response_type=code&scope=get_user_info%2Cadd_share%2Cadd_pic_t'
    try:
        browser.get(url)
    except TimeoutException:
        print('time out after 30 seconds when loading page')
        browser.execute_script('window.stop()')  # 当页面加载时间超过设定时间，通过执行Javascript
    browser.set_page_load_timeout(30)
    browser.implicitly_wait(10)
    browser.switch_to.frame('ptlogin_iframe')
    browser.implicitly_wait(1)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_id('switcher_plogin'))
    pLogin_a = browser.find_element_by_id('switcher_plogin')

    ActionChains(browser).click(pLogin_a).perform()

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_name('u'))
    username = browser.find_element_by_name('u')

    username.clear()
    username.send_keys(account)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_name('p'))
    password_e = browser.find_element_by_name('p')

    password_e.clear()
    password_e.send_keys(password)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_id('login_button'))
    login_button = browser.find_element_by_id('login_button')
    login_button.click()

#成功返回用户id
def change_login(browser, conn, account_values, account_sub):
    login(browser, account_values[account_sub][1], account_values[account_sub][2])
    # 判断是否被封号
    # 调用js
    browser.implicitly_wait(5)
    have_close = is_close(browser)
    if have_close == 0:
        #没封号
        #判断有无验证
        browser.implicitly_wait(9)
        have_verify = is_verify(browser)
        if have_verify == 1:
            # 有滑块验证
            # 切换账号
            cursor = conn.cursor()
            account_id = account_values[account_sub][0]
            cursor.execute('UPDATE account SET have_block=1 WHERE account_id=%s',
                           (account_id,))
            conn.commit()

            account_sub = account_sub + 1
            if account_sub == len(account_values):
                return 0
            result = change_login(browser, conn, account_values, account_sub)
            if result != 0:
                return result
        else:
            return account_sub+1
    else:
        # 被封号
        cursor = conn.cursor()
        account_id = account_values[account_sub][0]
        cursor.execute('UPDATE account SET is_close=1 WHERE account_id=%s',
                       (account_id,))
        conn.commit()
        account_sub = account_sub + 1
        if account_sub == len(account_values):
            return 0
        result = change_login(browser, conn, account_values, account_sub)
        if result != 0:
            return result
#登录获取cookie
def getCookie():
    browser = webdriver.Chrome()
    conn = mysql.connector.connect(user='root', password='', database='material_download')
    cursor = conn.cursor()
    cursor.execute('select * from account')
    account_values = cursor.fetchall()
    for value in account_values:
        type = value[3]
        if type == 1:
            QianTuLogin(browser, value[1], value[2])
            time.sleep(2)
            have_close = is_close(browser)
            if have_close == 1: #被封号
                #更新账号封号状态
                cursor.execute('UPDATE account SET is_close=1 WHERE account_id=%s', (value[0],))
                conn.commit()
                #更新cookie为空
                cursor.execute('select * from cookie where cookie_account_id = %s', (value[0],))
                account_values = cursor.fetchall()
                if len(account_values) == 0:
                    cursor.execute( 'insert into cookie (cookie_account_id, cookie_type, cookie_is_valid) values (%s, %s, %s)', (value[0], 1, 0))
                else:
                    cursor.execute('UPDATE cookie SET cookie_is_valid=0 WHERE cookie_account_id=%s', (value[0],))
                conn.commit()
                continue
            have_verify = is_verify(browser)
            if have_verify == 1: #有滑块验证
                # 更新账号封号状态
                cursor.execute('UPDATE account SET have_block=1 WHERE account_id = %s', (value[0],))
                conn.commit()
                # 更新cookie为空
                cursor.execute('select * from cookie where cookie_account_id = %s', (value[0],))
                account_values = cursor.fetchall()
                if len(account_values) == 0:
                    cursor.execute('insert into cookie (cookie_account_id, cookie_type, cookie_is_valid) values (%s, %s, %s)', (value[0], 1, 0))
                else:
                    cursor.execute('UPDATE cookie SET cookie_is_valid=0 WHERE cookie_account_id=%s', (value[0],))
                conn.commit()
                continue
            #正常
            time.sleep(10)
            cookies = browser.get_cookies()
            # print(cookies)
            cookies = json.dumps(cookies)

            cursor.execute('select * from cookie where cookie_account_id = %s', (value[0],))
            account_values = cursor.fetchall()
            if len(account_values) == 0:
                cursor.execute('insert into cookie (cookie_account_id, cookie_type, cookie_value, cookie_is_valid) values (%s, %s, %s, %s)', (value[0], 1, cookies, 1))
            else:
                cursor.execute('UPDATE cookie SET cookie_value=%s,cookie_is_valid=%s WHERE cookie_account_id=%s', (cookies, 1, value[0],))
            cursor.execute('UPDATE account SET have_block=%s,is_close=%s WHERE account_id=%s', (0, 0, value[0]))
            conn.commit()
        elif type == 2:
            pass
        elif type == 3:
            pass
        elif type == 4:
            pass
        elif type == 5:
            pass
        elif type == 6:
            pass
    conn.close()
    browser.close()





#千图登录
def QianTuLogin(browser, account, password):
    url = r'https://graph.qq.com/oauth2.0/show?which=Login&display=pc&client_id=100414805&redirect_uri=http%3A%2F%2Fwww.58pic.com%2Findex.php%3Fm%3Dlogin%26a%3Dcallback%26type%3Dqq&response_type=code&scope=get_user_info%2Cadd_share%2Cadd_pic_t'
    try:
        browser.get(url)
    except TimeoutException:
        print('time out after 30 seconds when loading page')
        browser.execute_script('window.stop()')  # 当页面加载时间超过设定时间，通过执行Javascript
    browser.set_page_load_timeout(30)
    browser.implicitly_wait(10)
    browser.switch_to.frame('ptlogin_iframe')
    browser.implicitly_wait(1)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_id('switcher_plogin'))
    pLogin_a = browser.find_element_by_id('switcher_plogin')

    ActionChains(browser).click(pLogin_a).perform()

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_name('u'))
    username = browser.find_element_by_name('u')

    username.clear()
    username.send_keys(account)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_name('p'))
    password_e = browser.find_element_by_name('p')

    password_e.clear()
    password_e.send_keys(password)

    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_id('login_button'))
    login_button = browser.find_element_by_id('login_button')
    login_button.click()



def is_close(browser):
    js = "var tags =  document.getElementsByTagName(\"*\");" \
         "for(let i=0;i<tags.length;i++){" \
         "let arr = tags[i].className.split(\" \");" \
         "for(let i=0;i<arr.length;i++){" \
         "if(arr[i] === \"risk-error\"){" \
         "return 1; } } } " \
         "return 0;"
    have_close = browser.execute_script(js)
    return have_close

def is_verify(browser):
    js = "var q=document.getElementById(\"newVcodeIframe\");" \
         "if(q == null){" \
         " return 0;}else{" \
         " var b = q.firstChild;" \
         " if(b==null){" \
         " return 0; " \
         " }else{" \
         " return 1;  } }"
    have_verify = browser.execute_script(js)
    return have_verify

def is_error_url(brower):
    js = "var str = document.querySelector('.error-code');" \
         "if(str == null){" \
         "return 0;}" \
         "var str2 = str.innerHTML;" \
         "if(str2 == 'ERR_NAME_NOT_RESOLVED'){" \
         "return 1;" \
         "}" \
         "return 0;"
    is_error = brower.execute_script(js)
    return is_error

def have_register(browser):
    try:
        WebDriverWait(browser, 60).until(browser.find_element_by_class_name('login-content'))
        return 1
    except:
        return 0

def getResponse(code, msg, data):
    return json.dumps({'code':code, 'msg':msg, 'data':data}, ensure_ascii=False, encoding='gb2312')

@server.route('/login', methods=['GET'])
def main():
    browser = webdriver.Chrome()
    browser.set_page_load_timeout(30)
    conn = mysql.connector.connect(user='root', password='', database='material_download')
    cursor = conn.cursor()
    account_sub = 0
    cursor.execute('select * from account where type = %s and have_block = 0 and is_close = 0', ('1',))
    account_values = cursor.fetchall()
    # 登陆,被封号或有滑块验证，立马切号
    user_id = change_login(browser, conn, account_values, account_sub)
    # if user_id == 0:
    #     # 判断ip是否被封
    #     url = r'http://www.58pic.com/'
    #     browser.get(url)
    #     has_close = is_close(browser)
    #     if has_close == 0:
    #         # 清除浏览数据
    #         browser.get('chrome://settings/clearBrowserData')
    #         s = WebDriverWait(browser, 60).until(Select(browser.find_element_by_id('dropdownMenu')))
    #         s.select_by_visible_text('近 4 周')
    #         clear_b = WebDriverWait(browser, 60).until(browser.find_element_by_id('clearBrowsingDataConfirm'))
    #         clear_b.click()
    #         # 清除cookie
    #         browser.delete_all_cookies()
    #         print('封ip')
    #     else:
    #         print('账号不够')
    time.sleep(100)


    # pinrt('html2')
    #print(browser.page_source)

    cookies = browser.get_cookies()
    cookies = json.dumps(cookies)
    cursor.execute('UPDATE config SET config_value=%s WHERE config_key=6',
                   [cookies])
    conn.commit()
    old_str = request.values.get('url')
    if old_str != None:
        # 内部调用

        # print(xx)
        return redirect(url_for('login', url=old_str))
    else:
        cursor.execute('UPDATE config SET config_value=1 WHERE config_key=7')
        conn.commit()
        return json.dumps({'code': 200, 'msg': '登录成功'})
    browser.close()


    # except:
    #     old_str = request.values.get('url')
    #     if old_str == None:
    #         return json.dumps({'code': 500, 'msg': '服务器错误'})



#异步
class myThread (threading.Thread):
    def __init__(self, threadID, href, oldHref, conn, cursor ,browser):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.href = href
        self.old_href = oldHref
        self.conn = conn
        self.cursor = cursor
        self.browser = browser

    def run(self):
        if self.threadID == 1: #返回链接
            return json.dumps({'code': 200, 'msg': '获取下载成功', 'data': {'href': self.href}})
        elif self.threadID == 2: #下载
            user_id = 2
            t = time.time()
            time_str = (int(round(t * 1000)))  # 毫秒时间戳
            zip_name = str(user_id) + "-" + str(time_str) + ".zip"
            r = requests.get(self.href, stream=True, verify=True, headers=headers)
            r.encoding = "utf-8"
            file_path = 'D:/code_file/php/materialDownload/public/static/py_file/'
            zip_name = file_path + zip_name
            with open(zip_name, 'wb+') as fd:
                for chunk in r.iter_content(1024 * 100):
                    fd.write(chunk)
            # 记录下载数据
            r = redis.StrictRedis(host='localhost', port=6379, db=0)
            r.hmset('file', {self.old_href: zip_name})

            conn = self.conn
            cursor = self.cursor
            cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
                           [self.old_href, zip_name, time_str])
            cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
                           [user_id, 1, time_str])
            conn.commit()
            self.browser.close()
            # return json.dumps({'code': 200, 'msg': '下载成功', 'data': {'href': href}})

        else:
            return 0


@asyncio.coroutine
def download2(browser, url, old_url, conn, cursor):
    user_id = 2
    t = time.time()
    time_str = (int(round(t * 1000)))  # 毫秒时间戳
    zip_name = str(user_id) + "-" + str(time_str) + ".zip"
    re = requests.get(url, stream=True, verify=True, headers=headers)
    re.encoding = "utf-8"
    file_path = 'D:/code_file/php/materialDownload/public/static/py_file/'
    zip_name = file_path + zip_name
    with open(zip_name, 'wb+') as fd:
        for chunk in re.iter_content(1024 * 100):
            fd.write(chunk)
    # 记录下载数据
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.hmset('file', {old_url: zip_name})

    conn = conn
    cursor = cursor
    cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
                   [old_url, zip_name, time_str])
    cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
                   [user_id, 1, time_str])
    conn.commit()
    browser.close()



@asyncio.coroutine
def getHref(href):
    return json.dumps({'code': 200, 'msg': '获取下载成功', 'data': {'href': href}})



# async def index(browser, url, old_url, conn, cursor):
#     await asyncio.sleep(0.5)
#     user_id = 2
#     t = time.time()
#     time_str = (int(round(t * 1000)))  # 毫秒时间戳
#     zip_name = str(user_id) + "-" + str(time_str) + ".zip"
#     re = requests.get(url, stream=True, verify=True, headers=headers)
#     re.encoding = "utf-8"
#     file_path = 'D:/code_file/php/materialDownload/public/static/py_file/'
#     zip_name = file_path + zip_name
#     with open(zip_name, 'wb+') as fd:
#         for chunk in re.iter_content(1024 * 100):
#             fd.write(chunk)
#     # 记录下载数据
#     r = redis.StrictRedis(host='localhost', port=6379, db=0)
#     r.hmset('file', {old_url: zip_name})
#
#     conn = conn
#     cursor = cursor
#     cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
#                    [old_url, zip_name, time_str])
#     cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
#                    [user_id, 1, time_str])
#     conn.commit()
#     browser.close()
#
# async def hello(href):
#     await asyncio.sleep(0.5)
#     return json.dumps({'code': 200, 'msg': '获取下载成功', 'data': {'href': href}})
#
# async def init(loop,browser, href, old_str, conn, cursor):
#     app = web.Application(loop=loop)
#     app.router.add_route('GET', '/download', index(browser, href, old_str, conn, cursor))
#     app.router.add_route('GET', '/download', hello(href))
#     srv = await loop.create_server(app.make_handler(), '127.0.0.1', 8000)
#     print('Server started at http://127.0.0.1:8000...')
#     return srv



@server.route('/download', methods=['GET'])
def download():
    browser = webdriver.Chrome()
    conn = mysql.connector.connect(user='root', password='', database='material_download')
    cursor = conn.cursor()

    # cursor.execute('select * from config where config_key = 6')
    cursor.execute('select * from cookie where cookie_type = %s and cookie_is_valid = 1 order by cookie_use_count desc',
                   (1,))
    account_values = cursor.fetchall()
    if len(account_values) == 0:
        return json.dumps({'code': 500, 'msg': '服务器错误'})

    old_str = request.values.get('url')
    if old_str == None:
        return json.dumps({'code': 500, 'msg': '缺少参数'})
    urlArr = old_str.split('/')
    old_str2 = urlArr[len(urlArr) - 1]
    url = r'https://dl.58pic.com/' + old_str2
    browser.get(url)

    # 判断链接是否有效
    time.sleep(2)
    try:
        browser.find_element_by_class_name('error_img2')
        return json.dumps({'code': 500, 'msg': '无效的链接，请输入正确的链接'})
    except:
        pass
    browser.get_cookies()
    browser.delete_all_cookies()
    cookies = json.loads(account_values[0][2])
    for cookie in cookies:  # 如果登陆界面获取cookie
        browser.add_cookie(cookie)  # 添加cookie ，通过Cookie登陆
    time.sleep(4)
    browser.get(url)
    # 找下载链接
    browser.implicitly_wait(6)
    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_class_name('autodown'))

    down_a = browser.find_element_by_class_name('autodown')
    href = down_a.get_attribute('href')

    # new_loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(new_loop)
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(init(loop, browser, href, old_str, conn, cursor))
    # loop.run_forever()



    # new_loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(new_loop)
    # loop = asyncio.get_event_loop()
    # tasks = [getHref(href), download2(browser, href, old_str, conn, cursor)]
    # loop.run_until_complete(asyncio.wait(tasks))
    # loop.close()

    # return json.dumps({'code': 200, 'msg': '获取下载成功', 'data': {'href': href}})



    #多线程
    # getHrefThread = myThread(1, href, old_str, conn, cursor, browser)   # threadID, href, oldHref, conn, browser
    # downloadThread = myThread(2, href, old_str, conn, cursor, browser)
    # getHrefThread.start()
    # downloadThread.start()
    # getHrefThread.join()
    # downloadThread.join()

    # return json.dumps({'code': 200, 'msg': '获取下载成功', 'data': {'href': href}})

    # 获取下载的文件到本地
    user_id = 2
    t = time.time()
    time_str = (int(round(t * 1000)))  # 毫秒时间戳
    zip_name = str(user_id) + "-" + str(time_str) + ".zip"
    r = requests.get(href, stream=True, verify=True, headers=headers)
    r.encoding = "utf-8"
    file_path = 'D:/code_file/php/materialDownload/public/static/py_file/'
    zip_name = file_path + zip_name
    with open(zip_name, 'wb+') as fd:
        for chunk in r.iter_content(1024 * 100):
            fd.write(chunk)
    # 记录下载数据
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.hmset('file',  {old_str: zip_name})

    cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
                   [old_str, zip_name, time_str])
    cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
                   [user_id, 1, time_str])
    conn.commit()
    browser.close()
    return json.dumps({'code': 200, 'msg': '下载成功'})

@server.route('/updateCookie', methods=['GET'])
def updateCookie():
    getCookie()
    return json.dumps({'code': 201, 'msg': '更新cookie成功'})



if __name__ == "__main__":
    #pass
    #main()
    server.run(debug=True)
    # server.run()

