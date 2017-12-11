import logging
import re
import weakref


_logger = logging.getLogger(__name__)

_sql_statements = weakref.WeakValueDictionary()

_int_re = re.compile(r'(?<!:)\b\d+\b')

_single_quotes_p = "'(?:[^']|'')*'"
_single_quotes_re = re.compile(_single_quotes_p)


_uncomment_sql_p = r'/\*.*?\*/'
_uncomment_sql_re = re.compile(_uncomment_sql_p, re.DOTALL)


def _uncomment_sql(sql):
    return _uncomment_sql_re.sub('', sql)


def _obfuscate_sql(sql):
    sql = _single_quotes_re.sub('?', sql)
    sql = _int_re.sub('?', sql)
    return sql


class SQLStatement(object):
    __slots__ = ['sql', 'database', '_operation', '_uncommented', '_obfuscated', '__weakref__']

    def __init__(self, sql, database=None):
        self.sql = sql
        self.database = database
        self._operation = None
        # self._target = None
        self._uncommented = None
        self._obfuscated = None

    @property
    def uncommented(self):
        if self._uncommented is None:
            self._uncommented = _uncomment_sql(self.sql)
        return self._uncommented

    @property
    def obfuscated(self):
        if self._obfuscated is None:
            self._obfuscated = _obfuscate_sql(self.uncommented)
        return self._obfuscated


def sql_statement(sql, dbapi2_module):
    key = (sql, dbapi2_module)
    result = _sql_statements.get(key, None)

    if result is not None:
        return result

    result = SQLStatement(sql, None)
    _sql_statements[key] = result
    return result
