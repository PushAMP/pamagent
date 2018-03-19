import wrapt

from pamagent.transaction_cache import current_transaction
from pamagent.trace import CacheTrace, wrap_cache_trace
from pamagent.wrapper import FuncWrapper

_redis_methods = frozenset(
    ("bgrewriteaof", "bgsave", "client_kill", "client_list", "client_getname", "client_setname", "config_get",
     "config_set", "config_resetstat", "config_rewrite", "dbsize", "debug_object", "echo", "flushall", "flushdb",
     "info", "lastsave", "object", "ping", "save", "sentinel", "sentinel_get_master_addr_by_name", "sentinel_master",
     "sentinel_masters", "sentinel_monitor", "sentinel_remove", "sentinel_sentinels", "sentinel_set", "sentinel_slaves",
     "shutdown", "slaveof", "slowlog_get", "slowlog_reset", "time", "append", "bitcount", "bitop", "bitpos", "decr",
     "delete", "dump", "exists", "expire", "expireat", "get", "getbit", "getrange", "getset", "incr", "incrby",
     "incrbyfloat", "keys", "mget", "mset", "msetnx", "move", "persist", "pexpire", "pexpireat", "psetex", "pttl",
     "randomkey", "rename", "renamenx", "restore", "set", "setbit", "setex", "setnx", "setrange", "strlen", "substr",
     "ttl", "type", "watch", "unwatch", "blpop", "brpop", "brpoplpush", "lindex", "linsert", "llen", "lpop", "lpush",
     "lpushx", "lrange", "lrem", "lset", "ltrim", "rpop", "rpoplpush", "rpush", "rpushx", "sort", "scan", "scan_iter",
     "sscan", "sscan_iter", "hscan", "hscan_inter", "zscan", "zscan_iter", "sadd", "scard", "sdiff", "sdiffstore",
     "sinter", "sinterstore", "sismember", "smembers", "smove", "spop", "srandmember", "srem", "sunion", "sunionstore",
     "zadd", "zcard", "zcount", "zincrby", "zinterstore", "zlexcount", "zrange", "zrangebylex", "zrangebyscore",
     "zrank", "zrem", "zremrangebylex", "zremrangebyrank", "zremrangebyscore", "zrevrange", "zrevrangebyscore",
     "zrevrank", "zscore", "zunionstore", "pfadd", "pfcount", "pfmerge", "hdel", "hexists", "hget", "hgetall",
     "hincrby", "hincrbyfloat", "hkeys", "hlen", "hset", "hsetnx", "hmset", "hmget", "hvals", "publish", "eval",
     "evalsha", "script_exists", "script_flush", "script_kill", "script_load", "setex", "lrem", "zadd")
)


def _instance_info(connection):
    host = getattr(connection, 'host', 'localhost')
    port = getattr(connection, 'port', 0)
    db = getattr(connection, 'db', 0)
    return host, int(port), str(db)


def redis_connection_wrapper(wrapped, product):

    def dynamic_wrapper(wrapped, *args):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args[1])
        host, port, db = _instance_info(args[0])
        try:
            method = args[1][0].lower()
        except (IndexError, AttributeError):
            method = None
        if method not in _redis_methods:
            return wrapped(*args[1])
        with CacheTrace(transaction, product, method, host=host, port=port, db=db):
            return wrapped(*args[1])

    return FuncWrapper(wrapped, dynamic_wrapper)


def instrument_redis_client(module):
    wrap_cache_trace(module, "Connection.send_command", "Redis", redis_connection_wrapper)


def path():
    wrapt.register_post_import_hook(instrument_redis_client, "redis.connection")
