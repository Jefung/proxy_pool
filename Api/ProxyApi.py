# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""
-------------------------------------------------
   File Name：     ProxyApi.py
   Description :   WebApi
   Author :       JHao
   date：          2016/12/4
-------------------------------------------------
   Change Activity:
                   2016/12/04: WebApi
                   2019/08/14: 集成Gunicorn启动方式
-------------------------------------------------
"""
import logging

from Manager.AsdlProxyManager import AsdlProxyManager
from ProxyHelper import Proxy
from Util import LogHandler

__author__ = 'JHao'

import sys
import platform
from werkzeug.wrappers import Response
from flask import Flask, jsonify, request
from flask_httpauth import HTTPBasicAuth
from flask import abort

auth = HTTPBasicAuth()

sys.path.append('../')

from Config.ConfigGetter import config
from Manager.ProxyManager import ProxyManager

app = Flask(__name__)


class JsonResponse(Response):
    @classmethod
    def force_type(cls, response, environ=None):
        if isinstance(response, (dict, list)):
            response = jsonify(response)

        return super(JsonResponse, cls).force_type(response, environ)


app.response_class = JsonResponse

api_list = {
    'get': u'get an useful proxy',
    # 'refresh': u'refresh proxy pool',
    'get_all': u'get all proxy from proxy pool',
    'delete?proxy=127.0.0.1:8080': u'delete an unable proxy',
    'get_status': u'proxy number'
}


@app.route('/')
def index():
    return api_list


@app.route('/get/')
def get():
    proxy = ProxyManager().get()
    return proxy.info_json if proxy else {"code": 0, "src": "no proxy"}


@app.route('/refresh/')
def refresh():
    # TODO refresh会有守护程序定时执行，由api直接调用性能较差，暂不使用
    # ProxyManager().refresh()
    pass
    return 'success'


@app.route('/get_all/')
def getAll():
    proxies = ProxyManager().getAll()
    return [_.info_dict for _ in proxies]


@app.route('/delete/', methods=['GET'])
def delete():
    proxy = request.args.get('proxy')
    ProxyManager().delete(proxy)
    return {"code": 0, "src": "success"}


@app.route('/get_status/')
def getStatus():
    status = ProxyManager().getNumber()
    return status


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello'})


def gen_response(code, msg):
    response = jsonify({'message': msg})
    response.status_code = code
    return response


@app.route('/adsl_proxy/add', methods=["POST"])
@auth.login_required
def add_adsl_proxy():
    proxy_str = request.form.get('proxy', None)  # 以字典形式获取参数
    if proxy_str is None:
        return gen_response(400, "invalid input")
    try:
        AsdlProxyManager().add_asdl_proxy(proxy_str)
    except Exception as e:
        return gen_response(400, str(e))
    return gen_response(200, "success")


@app.route('/adsl_proxy/delete', methods=["POST"])
@auth.login_required
def delete_adsl_proxy():
    proxy_str = request.form.get('proxy', None)  # 以字典形式获取参数
    api_log.info("access delete_adsl_proxy, proxy: " + str(proxy_str))
    if proxy_str is None:
        return gen_response(400, "invalid input")
    try:
        AsdlProxyManager().delete_asdl_proxy(proxy_str)
        proxies = AsdlProxyManager().get_all_proxy()
        ls = [_.info_dict for _ in proxies]
        api_log.info("after access delete_adsl_proxy, proxies in db: " +
                     str(ls))
    except Exception as e:
        api_log.error("access delete_adsl_proxy error, proxy: " +
                      str(proxy_str) + ", err: " + str(e))
        return gen_response(400, str(e))

    return gen_response(200, "success")


@app.route('/adsl_proxy/get_all', methods=["GET"])
@auth.login_required
def get_all_adsl_proxy():
    try:
        proxies = AsdlProxyManager().get_all_proxy()
        return [_.info_dict for _ in proxies]
    except Exception as e:
        return gen_response(400, str(e))


@auth.verify_password
def verify_password(username, password):
    if config.api_password is None or config.api_username is None:
        return True
    if username == config.api_username and password == config.api_password:
        return True
    else:
        return False


if platform.system() != "Windows":
    import gunicorn.app.base
    from six import iteritems

    class StandaloneApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super(StandaloneApplication, self).__init__()

        def load_config(self):
            _config = dict([(key, value)
                            for key, value in iteritems(self.options)
                            if key in self.cfg.settings and value is not None])
            for key, value in iteritems(_config):
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application


def runFlask():
    app.run(host=config.host_ip, port=config.host_port, threaded=True)


def runFlaskWithGunicorn():
    _options = {
        'bind': '%s:%s' % (config.host_ip, config.host_port),
        'workers': 4,
        'accesslog': '-',  # log to stdout
        'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
    }
    StandaloneApplication(app, _options).run()


api_log = LogHandler("api")


def main():
    app.debug = True
    # for handler in api_log.handlers:
    #     app.logger.addHandler(handler)
    api_log.info("api start")
    if platform.system() == "Windows":
        runFlask()
    else:
        runFlaskWithGunicorn()


if __name__ == '__main__':
    main()
