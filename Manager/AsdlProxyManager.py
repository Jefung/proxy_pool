from DB.DbClient import DbClient

from ProxyHelper import Proxy

from time import gmtime, strftime
from datetime import datetime


class AsdlProxyManager():
    def __init__(self):
        self.asdl_proxy_queue = "asdl_proxy"
        self.db = DbClient()

    def add_asdl_proxy(self, proxy_str):
        proxy = Proxy(proxy_str,
                      last_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.db.changeTable(self.asdl_proxy_queue)
        self.db.put(proxy)

    def delete_asdl_proxy(self, proxy_str):
        self.db.changeTable(self.asdl_proxy_queue)
        self.db.delete(proxy_str)

    def get_all_proxy(self):
        self.db.changeTable(self.asdl_proxy_queue)
        item_list = self.db.getAll()
        return [Proxy.newProxyFromJson(_) for _ in item_list]
