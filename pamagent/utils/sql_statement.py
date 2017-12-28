import logging
import re
import weakref

_logger = logging.getLogger(__name__)

_sql_statements = weakref.WeakValueDictionary()

_int_re = re.compile(r'(?<!:)\b\d+\b')

_single_quotes_p = "'(?:[^']|'')*'"
_single_quotes_re = re.compile(_single_quotes_p)
_double_quotes_p = '"(?:[^"]|"")*"'
_double_quotes_re = re.compile(_double_quotes_p)
_any_quotes_p = _single_quotes_p + '|' + _double_quotes_p
_any_quotes_re = re.compile(_any_quotes_p)

_uncomment_sql_p = r'/\*.*?\*/'
_uncomment_sql_re = re.compile(_uncomment_sql_p, re.DOTALL)


_quotes_table = {
    'single': _single_quotes_re,
    'double': _double_quotes_re,
    'single+double': _any_quotes_re,
}


def _uncomment_sql(sql):
    return _uncomment_sql_re.sub('', sql)


def _obfuscate_sql(sql, quoting_style):
    quotes_re = _quotes_table.get(quoting_style, _single_quotes_re)
    sql = quotes_re.sub('?', sql)
    sql = _int_re.sub('?', sql)
    return sql


_parse_identifier_1_p = r'"((?:[^"]|"")+)"(?:\."((?:[^"]|"")+)")?'
_parse_identifier_2_p = r"'((?:[^']|'')+)'(?:\.'((?:[^']|'')+)')?"
_parse_identifier_3_p = r'`((?:[^`]|``)+)`(?:\.`((?:[^`]|``)+)`)?'
_parse_identifier_4_p = r'\[\s*(\S+)\s*\]'
_parse_identifier_5_p = r'\(\s*(\S+)\s*\)'
_parse_identifier_6_p = r'([^\s\(\)\[\],]+)'

_parse_identifier_p = ''.join(('(', _parse_identifier_1_p, '|',
                               _parse_identifier_2_p, '|', _parse_identifier_3_p, '|',
                               _parse_identifier_4_p, '|', _parse_identifier_5_p, '|',
                               _parse_identifier_6_p, ')'))

_parse_from_p = '\s+FROM\s+' + _parse_identifier_p
_parse_from_re = re.compile(_parse_from_p, re.IGNORECASE)
_parse_update_p = '\s*UPDATE\s+' + _parse_identifier_p
_parse_update_re = re.compile(_parse_update_p, re.IGNORECASE)
_parse_into_p = '\s+INTO\s+' + _parse_identifier_p
_parse_into_re = re.compile(_parse_into_p, re.IGNORECASE)
_parse_call_p = r'\s*CALL\s+(?!\()(\w+)'
_parse_call_re = re.compile(_parse_call_p, re.IGNORECASE)

_identifier_re = re.compile('[\',"`\[\]\(\)]*')


def _extract_identifier(token):
    return _identifier_re.sub('', token).strip().lower()


def _parse_default(sql, regex):
    match = regex.search(sql)
    return match and _extract_identifier(match.group(1)) or ''


def _join_identifier(m):
    return m and '.'.join([s for s in m.groups()[1:] if s]).lower() or ''


def _parse_select(sql):
    return _join_identifier(_parse_from_re.search(sql))


def _parse_delete(sql):
    return _join_identifier(_parse_from_re.search(sql))


def _parse_insert(sql):
    return _join_identifier(_parse_into_re.search(sql))


def _parse_update(sql):
    return _join_identifier(_parse_update_re.search(sql))


def _parse_call(sql):
    return _parse_default(sql, _parse_call_re)


_operation_table = {
    'select': _parse_select,
    'delete': _parse_delete,
    'insert': _parse_insert,
    'update': _parse_update,
    'create': None,
    'drop': None,
    'call': _parse_call,
    'show': None,
    'set': None,
    'exec': None,
    'execute': None,
    'alter': None,
    'commit': None,
    'rollback': None,
}

_parse_operation_p = r'(\w+)'
_parse_operation_re = re.compile(_parse_operation_p)


def _parse_operation(sql):
    match = _parse_operation_re.search(sql)
    operation = match and match.group(1).lower() or ''
    return operation if operation in _operation_table else ''


def _parse_target(sql, operation):
    parse = _operation_table.get(operation, None)
    return parse and parse(sql) or ''


class SQLStatement(object):
    __slots__ = ['sql', 'quoting_style', '_operation', '_uncommented', '_obfuscated', '__weakref__', '_target']

    def __init__(self, sql, quoting_style=None):
        self.sql = sql
        self.quoting_style = quoting_style
        self._operation = None
        self._target = None
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
            self._obfuscated = _obfuscate_sql(self.uncommented, self.quoting_style)
        return self._obfuscated

    @property
    def operation(self):
        if self._operation is None:
            self._operation = _parse_operation(self.uncommented)
        return self._operation

    @property
    def target(self):
        if self._target is None:
            self._target = _parse_target(self.uncommented, self.operation)
        return self._target


def sql_statement(sql, dbapi2_module):
    key = (sql, dbapi2_module)
    result = _sql_statements.get(key, None)

    if result is not None:
        return result

    result = SQLStatement(sql, getattr(dbapi2_module, "_pam_quoting_style", None))
    _sql_statements[key] = result
    return result
