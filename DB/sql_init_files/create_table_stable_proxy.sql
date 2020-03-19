-- 稳定代理表, 保存个人稳定的代理
create table if not exists stable_proxy
(
    id      INTEGER not null
        constraint stable_proxy_pk
            primary key AUTOINCREMENT,
    host_id string  not null unique, -- 提供代理主机的标识符, 自定义
    proxy   string  not null,        -- 代理主机可用的proxy
    meta    string                   -- 代理主机的信息
);
