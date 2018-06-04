import requests
import sys
import io
import PIL.Image as image
import time,re, random
import mysql.connector
import json
import flask
from flask import request,redirect,url_for #想获取到请求参数的话，就得用这个
from pyvirtualdisplay import Display #linux
server = flask.Flask(__name__) #把这个python文件当做一个web服务

from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support.ui import Select

from selenium.webdriver import ActionChains
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops


#爬虫模拟的浏览器头部信息
# agent = "Mozilla/5.0 (Windows NT 5.1; rv:33.0) Gecko/20100101 Firefox/33.0"
# agent = "Mozilla/5.0 (iPod; U; CPU iPhone OS 2_1 like Mac OS X; ja-jp) AppleWebKit/525.18.1 (KHTML, like Gecko) Version/3.1.1 Mobile/5F137 Safari/525.20"
agent = 'MMozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0'
headers = {
        "User-Agent": agent
        }



def database():
    conn = mysql.connector.connect(user='root', password='ZC123', database='material_download')
    return conn.cursor()

def login(browser, account, password):
    url = r'https://graph.qq.com/oauth2.0/show?which=Login&display=pc&client_id=100414805&redirect_uri=http%3A%2F%2Fwww.58pic.com%2Findex.php%3Fm%3Dlogin%26a%3Dcallback%26type%3Dqq&response_type=code&scope=get_user_info%2Cadd_share%2Cadd_pic_t'
    browser.get(url)
    browser.implicitly_wait(3)
    browser.switch_to.frame('ptlogin_iframe')
    browser.implicitly_wait(1)
    pLogin_a = browser.find_element_by_id('switcher_plogin')
    pLogin_a.click()
    username = browser.find_element_by_name('u')
    username.clear()
    username.send_keys(account)
    password_e = browser.find_element_by_name('p')
    password_e.clear()
    password_e.send_keys(password)
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
            account_values = cursor.rowcount
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
        account_values = cursor.rowcount
        conn.commit()
        account_sub = account_sub + 1
        if account_sub == len(account_values):
            return 0
        result = change_login(browser, conn, account_values, account_sub)
        if result != 0:
            return result

def is_close(browser):
    js = "var tags =  document.getElementsByTagName(\"*\");" \
         "for(let i=0;i<tags.length;i++){" \
         "let arr = tags[i].className.split(\" \");" \
         "for(let i=0;i<arr.length;i++){" \
         "if(arr[i] === \"risk-error\"){" \
         "return 1; } } } " \
         "return 0;"
    # have_close = WebDriverWait(browser, 60).until(browser.execute_script(js))
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
   # have_verify = WebDriverWait(browser, 60).until(browser.execute_script(js))
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
    # try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # 改变标准输出的默认编码

    # 建立Phantomjs浏览器对象，括号里是phantomjs.exe在你的电脑上的路径
    # browser = webdriver.PhantomJS('d:/tool/07-net/phantomjs-windows/phantomjs-2.1.1-windows/bin/phantomjs.exe')

    # linux
    display = Display(visible=0, size=(800, 800))
    display.start()
    browser = webdriver.Chrome()
    conn = mysql.connector.connect(user='root', password='ZC123', database='material_download')
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

    time.sleep(15)
    cookies = browser.get_cookies()
    cookies = json.dumps(cookies)
    cursor.execute('UPDATE config SET config_value=%s WHERE config_key=6',
                   [cookies])
    account_values = cursor.rowcount
    conn.commit()
    old_str = request.values.get('url')
    if old_str != None:
        # 内部调用
        return redirect(url_for('login', url=old_str))
    else:
        cursor.execute('UPDATE config SET config_value=1 WHERE config_key=7')
        account_values = cursor.rowcount
        conn.commit()
        return json.dumps({'code': 200, 'msg': '登录成功'})



    # except:
    #     old_str = request.values.get('url')
    #     if old_str == None:
    #         return json.dumps({'code': 500, 'msg': '服务器错误'})



@server.route('/download', methods=['GET'])
def download():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # 改变标准输出的默认编码
    # 建立Phantomjs浏览器对象，括号里是phantomjs.exe在你的电脑上的路径
    # browser = webdriver.PhantomJS('d:/tool/07-net/phantomjs-windows/phantomjs-2.1.1-windows/bin/phantomjs.exe')

    # linux
    display = Display(visible=0, size=(800, 800))
    display.start()

    browser = webdriver.Chrome()
    conn = mysql.connector.connect(user='root', password='ZC123', database='material_download')
    cursor = conn.cursor()
    cursor.execute('select * from config where config_key = 6')
    account_values = cursor.fetchall()
    # 访问下载页面  https://dl.58pic.com/28538518.html

    # return json.dumps({'code': 500, 'msg': 'sss', 'data': 122})

    old_str = request.values.get('url')
    if old_str == None:
        return json.dumps({'code': 500, 'msg': '缺少参数'})

    urlArr = old_str.split('/')
    # len(urlArr)
    old_str2 = urlArr[len(urlArr) - 1]
    url = r'https://dl.58pic.com/' + old_str2
    # old_str2 = old_str.replace('http://www.58pic.com/newpic/', '', 1)
    # url = r'https://dl.58pic.com/' + old_str2
    browser.get(url)
    # try:
    #     browser.get(url)
    # except:
    #     return json.dumps({'code': 500, 'msg': '无效的url'})
    #is_error = is_error_url(browser)
    #if is_error == 1:
    #   return json.dumps({'code': 500, 'msg': '无效的url'})
    browser.get_cookies()
    browser.delete_all_cookies()
    cookies = json.loads(account_values[0][2])
    for cookie in cookies:  # 如果登陆界面获取cookie
        browser.add_cookie(cookie)  # 添加cookie ，通过Cookie登陆
    time.sleep(10)
    browser.get(url)
    # 判断登录是否失效
    # regis = have_register(browser)
    #         # if regis == 1:
    #         #     return redirect(url_for('login', url=old_str, is_api=1))

    # 找下载链接
    browser.implicitly_wait(6)
    # time.sleep(100)
    WebDriverWait(browser, 200).until(lambda the_driver: the_driver.find_element_by_class_name('autodown'))
    down_a = browser.find_element_by_class_name('autodown')
    href = down_a.get_attribute('href')

    # 获取下载的文件到本地
    user_id = 2
    t = time.time()
    time_str = (int(round(t * 1000)))  # 毫秒时间戳
    zip_name = str(user_id) + "-" + str(time_str) + ".zip"
    r = requests.get(href, stream=True, verify=True, headers=headers)
    # r = requests.get(url=url)
    r.encoding = "utf-8"
    file_path = 'F:/php_project/materialDownload/public/static/py_file/'
    zip_name = file_path + zip_name
    with open(zip_name, 'wb+') as fd:
        for chunk in r.iter_content(1024 * 100):
            fd.write(chunk)
    # 记录下载数据
    cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
                   [old_str, zip_name, time_str])
    cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
                   [user_id, 1, time_str])
    account_values = cursor.rowcount
    conn.commit()
    #browser.close()
    return json.dumps({'code': 200, 'msg': '下载成功'})












    # try:
    #     browser = webdriver.Chrome()
    #     conn = mysql.connector.connect(user='root', password='123456', database='material_download')
    #     cursor = conn.cursor()
    #     cursor.execute('select * from config where config_key = 6')
    #     account_values = cursor.fetchall()
    #     # 访问下载页面  https://dl.58pic.com/28538518.html
    #
    #     # return json.dumps({'code': 500, 'msg': 'sss', 'data': 122})
    #
    #     old_str = request.values.get('url')
    #     if old_str == None:
    #         return json.dumps({'code': 500, 'msg': '缺少参数'})
    #     # old_str = 'http://www.58pic.com/newpic/28453253.html'
    #     old_str2 = old_str.replace('http://www.58pic.com/newpic/', '', 1)
    #     url = r'https://dl.58pic.com/' + old_str2
    #     browser.get(url)
    #     browser.get_cookies()
    #     browser.delete_all_cookies()
    #     cookies = json.loads(account_values[0][2])
    #     #cookies = account_values[0][2]
    #     for cookie in cookies:  # 如果登陆界面获取cookie
    #       browser.add_cookie(cookie)  # 添加cookie ，通过Cookie登陆
    #     #browser.get(url)
    #     #判断登录是否失效
    #     # regis = have_register(browser)
    #     #         # if regis == 1:
    #     #         #     return redirect(url_for('login', url=old_str, is_api=1))
    #
    #     # 找下载链接
    #     browser.implicitly_wait(6)
    #     down_a = WebDriverWait(browser, 60).until(browser.find_element_by_class_name('autodown'))
    #     href = WebDriverWait(browser, 60).until(down_a.get_attribute('href'))
    #
    #     # 获取下载的文件到本地
    #     user_id = 2
    #     t = time.time()
    #     time_str = (int(round(t * 1000)))  # 毫秒时间戳
    #     zip_name = str(user_id) + "-" + str(time_str) + ".zip"
    #     r = requests.get(href, stream=True, verify=True, cookies=cookies)
    #     # r = requests.get(url=url)
    #     r.encoding = "utf-8"
    #     file_path = 'F:/php_project/materialDownload/public/static/py_file/'
    #     zip_name = file_path + zip_name
    #     with open(zip_name, 'wb+') as fd:
    #         for chunk in r.iter_content(1024 * 100):
    #             fd.write(chunk)
    #     # 记录下载数据
    #     cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
    #                    [url, zip_name, time_str])
    #     cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
    #                    [user_id, 1, time_str])
    #     account_values = cursor.rowcount
    #     conn.commit()
    #     return json.dumps({'code': 200, 'msg': '下载成功'})
    # except:
    #     return json.dumps({'code':500, 'msg':'服务器错误'})








# @server.route('/download2', methods=['GET'])
# def download():
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # 改变标准输出的默认编码
#     # 建立Phantomjs浏览器对象，括号里是phantomjs.exe在你的电脑上的路径
#     # browser = webdriver.PhantomJS('d:/tool/07-net/phantomjs-windows/phantomjs-2.1.1-windows/bin/phantomjs.exe')
#     browser = webdriver.Chrome()
#     conn = mysql.connector.connect(user='root', password='123456', database='material_download')
#     cursor = conn.cursor()
#     cursor.execute('select * from config where config_key = 6')
#     account_values = cursor.fetchall()
#     # 访问下载页面  https://dl.58pic.com/28538518.html
#
#     # return json.dumps({'code': 500, 'msg': 'sss', 'data': 122})
#
#     old_str = request.values.get('url')
#     if old_str == None:
#         return json.dumps({'code': 500, 'msg': '缺少参数'})
#     # old_str = 'http://www.58pic.com/newpic/28453253.html'
#     old_str2 = old_str.replace('http://www.58pic.com/newpic/', '', 1)
#     url = r'https://dl.58pic.com/' + old_str2
#     browser.get(url)
#     browser.get_cookies()
#     browser.delete_all_cookies()
#     cookies = json.loads(account_values[0][2])
#     # cookies = account_values[0][2]
#     for cookie in cookies:  # 如果登陆界面获取cookie
#         browser.add_cookie(cookie)  # 添加cookie ，通过Cookie登陆
#     # browser.get(url)
#     # 判断登录是否失效
#     # regis = have_register(browser)
#     #         # if regis == 1:
#     #         #     return redirect(url_for('login', url=old_str, is_api=1))
#
#     # 找下载链接
#     browser.implicitly_wait(6)
#     down_a = WebDriverWait(browser, 60).until(browser.find_element_by_class_name('autodown'))
#     href = WebDriverWait(browser, 60).until(down_a.get_attribute('href'))
#
#     # 获取下载的文件到本地
#     user_id = 2
#     t = time.time()
#     time_str = (int(round(t * 1000)))  # 毫秒时间戳
#     zip_name = str(user_id) + "-" + str(time_str) + ".zip"
#     r = requests.get(href, stream=True, verify=True, cookies=cookies)
#     # r = requests.get(url=url)
#     r.encoding = "utf-8"
#     file_path = 'F:/php_project/materialDownload/public/static/py_file/'
#     zip_name = file_path + zip_name
#     with open(zip_name, 'wb+') as fd:
#         for chunk in r.iter_content(1024 * 100):
#             fd.write(chunk)
#     # 记录下载数据
#     cursor.execute('INSERT INTO file (download_url, file_url, download_time) VALUES (%s, %s, %s)',
#                    [url, zip_name, time_str])
#     cursor.execute('INSERT INTO download_log (log_user_id, log_download_times, log_date) VALUES (%s, %s, %s)',
#                    [user_id, 1, time_str])
#     account_values = cursor.rowcount
#     conn.commit()
#     return json.dumps({'code': 200, 'msg': '下载成功'})








#主函数入口
if __name__ == "__main__":
    #pass
    #main()
    server.run(debug=True)
    # server.run()



#网页截图
#browser.save_screenshot('picture1.png')
#打印网页源代码
#print(browser.page_source.encode('utf-8').decode())

#browser.quit()