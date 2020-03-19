-- auto-generated definition
create table if not exists useful_proxy
(
    id          INTEGER not null
        constraint raw_proxy_pk
            primary key AUTOINCREMENT,
    proxy       string  not null
        unique,
    fail_count  int    default 0,
    region      string default "",
    type        string,
    source      string,
    check_count int    default 0,
    last_status int    default 0,
    last_time   string
);

