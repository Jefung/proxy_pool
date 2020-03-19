import os
from logging.handlers import TimedRotatingFileHandler
import re
import time
import requests
from requests.exceptions import ConnectionError, ReadTimeout
import subprocess

# 代理运行端口,用户名,密码
PROXY_PORT = 3333
PROXY_USERNAME = ""
PROXY_PASSWORD = ""

# 远端服务器ip, 用于同步ip
SYNC_SERVER = ""
SYNC_SERVER_USERNAME = ""
SYNC_SERVER_PASSWORD = ""

# 测试URL
TEST_URL = 'http://www.baidu.com'
# 测试超时时间
TEST_TIMEOUT = 20
# 拨号间隔
ADSL_CYCLE = 60
# 拨号出错重试间隔
ADSL_ERROR_CYCLE = 5
# ADSL命令, 由于连续拨号会有问题,所以中间sleep 1秒
ADSL_BASH = 'pppoe-stop;sleep 1;pppoe-start'
GET_IP_BY_HTTP = "curl -s ifconfig.co"
GET_IP_BY_IFCONFIG = "ifconfig"

# 客户端唯一标识
import logging


def get_logger():
    logging_file_path = os.path.join(os.path.dirname(__file__),
                                     "log/adsl_auto_dial.log")
    not os.path.exists(os.path.dirname(logging_file_path)) and os.mkdir(
        os.path.dirname(logging_file_path))
    # 输出到文件，并按小时分类
    logger = logging.getLogger("adsl_auto_dial")
    logger.setLevel(logging.DEBUG)
    handle = TimedRotatingFileHandler(logging_file_path,
                                      when='H',
                                      encoding="utf-8",
                                      backupCount=24)
    handle.setLevel(logging.INFO)
    handle.setFormatter(
        logging.Formatter('[%(level'
                          'name)s] %(asc'
                          'time)s %(filename)s:%(lineno)s %(message)s'))
    logger.addHandler(handle)

    # 输出到控制台
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(
        logging.Formatter('[%(level'
                          'name)s] %(asc'
                          'time)s %(filename)s:%(lineno)s %(message)s'))
    logger.addHandler(console)
    return logger


log = get_logger()


def get_ip():
    (status, output) = subprocess.getstatusoutput(GET_IP_BY_IFCONFIG)
    if status == 0:
        ips = re.findall("ppp\d[\s\S]*?inet addr:(\d+\.\d+\.\d+\.\d+)", output)
        if len(ips) == 0:
            log.error("can't match ip, ifconfig output: " + str(output))
            return

        if len(ips) == 1:
            ip = ips[0]
            log.info("get  ip by `{CMD}`: {IP}".format(CMD=GET_IP_BY_IFCONFIG,
                                                       IP=ip))
            return ip

        log.info("get multi ip, ips: " + str(ips))
        (status, output) = subprocess.getstatusoutput(GET_IP_BY_HTTP)
        if status == 0:
            ip = output
            if ip in ips:
                log.info("get  ip by `{CMD}`: {IP}".format(CMD=GET_IP_BY_HTTP,
                                                           IP=ip))
                return ip
            else:
                log.error("exec cmd `{CMD}` error, err: {ERR}".format(
                    CMD=GET_IP_BY_HTTP, ERR=str(output)))
        else:
            log.error("exec cmd `ifconfig` error, err: " + str(output))


def retry(tries=3, delay=0.1):
    def decorator(func):
        def wrapper(*args, **kw):
            count = 0
            while count < tries:
                try:
                    return func(*args, **kw)
                except Exception as e:
                    count += 1
                    if count != tries:
                        log.warning(
                            "retry {F} {TIME} time, exception: {E}".format(
                                F=func.__name__, TIME=count, E=str(e)))
                time.sleep(delay)
            log.error("retry {F} {TIME} time, but all failed".format(
                F=func.__name__, TIME=count))

        return wrapper

    return decorator


@retry()
def remove_proxy(proxy) -> bool:
    log.info("remove_proxy: " + proxy)
    url = "http://{HOST}/adsl_proxy/delete".format(HOST=SYNC_SERVER)
    payload = {'proxy': proxy}
    r = requests.post(url,
                      data=payload,
                      auth=(SYNC_SERVER_USERNAME, SYNC_SERVER_PASSWORD))
    if r.status_code != 200:
        log.error("request url `{}` not return 200, status_code: {}".format(
            url, r.status_code))
        raise Exception("http request err")


@retry()
def add_proxy(proxy) -> bool:
    log.info("add_proxy: " + proxy)
    url = "http://{HOST}/adsl_proxy/add".format(HOST=SYNC_SERVER)
    payload = {'proxy': proxy}
    r = requests.post(url,
                      data=payload,
                      auth=(SYNC_SERVER_USERNAME, SYNC_SERVER_PASSWORD))
    if r.status_code != 200:
        log.error("request url `{}` not return 200, status_code: {}".format(
            url, r.status_code))
        raise Exception("http request err")


def get_proxy(ip):
    return "http://{USERNAME}:{PASSWORD}@{IP}:{PORT}".format(
        USERNAME=PROXY_USERNAME,
        PASSWORD=PROXY_PASSWORD,
        IP=ip,
        PORT=PROXY_PORT,
    )


@retry
def test_proxy(proxy):
    log.info("test_proxy: " + proxy)
    url = TEST_URL
    r = requests.get(url, proxy=proxy)
    if r.status_code != 200:
        log.error("request url `{}` not return 200, status_code: {}".format(
            url, r.status_code))
        raise Exception("http request err")
    return True


def redial():
    while True:
        current_ip = get_ip()
        if current_ip is None:
            log.warning("current ip is None, ignore remove proxy")
        else:
            proxy = get_proxy(current_ip)
            remove_proxy(proxy)

        log.info("exec: " + ADSL_BASH)
        start = time.time()
        (status, output) = subprocess.getstatusoutput(ADSL_BASH)
        end = time.time()
        log.info("exec `{}` cost {}S".format(ADSL_BASH, end - start))
        if status == 0:
            log.info("redial Successfully")
            ip = get_ip()
            if ip:
                log.info("new IP: " + ip)
                proxy = get_proxy(ip)
                if test_proxy(proxy):
                    add_proxy(proxy)
                    break
                else:
                    log.error("Invalid Proxy: " + proxy)
            else:
                log.error("Get Ip failed, Re Dialing")
                time.sleep(ADSL_ERROR_CYCLE)
        else:
            log.error("ADSL Failed, Please Check")
            time.sleep(ADSL_ERROR_CYCLE)


if __name__ == '__main__':
    # add_proxy("http://jefung:GTx1nkNXNqkTydq6@115.230.64.7:4444")
    while True:
        log.info("start redial..................")
        redial()
        log.info("end redial....................")
        time.sleep(ADSL_CYCLE)
