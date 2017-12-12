import logging
import sys
import time
import urllib.parse

from .trace import FunctionTrace
from .transaction import Transaction
from .transaction_cache import set_transaction_name
from .wrapper import callable_name, FuncWrapper


_logger = logging.getLogger(__name__)


class WebTransaction(Transaction):
    def __init__(self, environ):  # flake8: noqa
        # The web transaction can be enabled/disabled by the value of the variable "pamagent.enabled" in the WSGI
        # environ dictionary.
        enabled = True
        self._port = None
        self._request_params = {}
        super(WebTransaction, self).__init__(enabled)
        self._name = "Uri"
        if not self.enabled:
            return
        port = environ.get('SERVER_PORT')
        try:
            self._port = int(port)
        except ValueError:
            _logger.error("SERVER_PORT is not valid. Found %s expected integer" % port)

        self._request_uri = environ.get('REQUEST_URI', None)
        script_name = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)

        if self._request_uri is not None:
            self._request_uri = urllib.parse.urlparse(self._request_uri)[2]

        if script_name is not None or path_info is not None:
            if path_info is None:
                self._path = script_name
            elif script_name is None:
                self._path = path_info
            else:
                self._path = script_name + path_info

            # self.save_transaction()

            if self._request_uri is None:
                self._request_uri = self._path
        else:
            if self._request_uri is not None:
                self._path = self._request_uri
                self.save_transaction()

        qs = environ.get('QUERY_STRING', None)
        if qs:
            params = urllib.parse.parse_qs(qs, keep_blank_values=True)
            self._request_params.update(params)
        self.url_name = 'unknown'
        self.view_name = 'unknown'


class _WSGIInputWrapper(object):
    def __init__(self, transaction, input_stream):
        self.__transaction = transaction
        self.__input = input_stream

    def __getattr__(self, name):
        return getattr(self.__input, name)

    def close(self):
        if hasattr(self.__input, 'close'):
            self.__input.close()

    def read(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            data = self.__input.read(*args, **kwargs)
        finally:
            self.__transaction._read_end = time.time()
        return data

    def readline(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            line = self.__input.readline(*args, **kwargs)
        finally:
            self.__transaction._read_end = time.time()
        return line

    def readlines(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            lines = self.__input.readlines(*args, **kwargs)
        finally:
            self.__transaction._read_end = time.time()
        return lines


def WSGIApplicationWrapper(wrapped, application=None, name=None, group=None, framework=None):
    if framework is not None and not isinstance(framework, tuple):
        framework = (framework, None)

    def _pam_wsgi_application_wrapper_(wrapped, instance, args, kwargs):


        def _args(environ, start_response, *args, **kwargs):
            return environ, start_response

        environ, _ = _args(*args, **kwargs)

        transaction = WebTransaction(environ)
        if framework is not None:
            transaction._name = callable_name(wrapped)

        elif name:
            transaction._name = name
        transaction.__enter__()
        if name is None:
            set_transaction_name(callable_name(wrapped))
        else:
            set_transaction_name(name)

        try:
            if 'wsgi.input' in environ:
                environ['wsgi.input'] = _WSGIInputWrapper(transaction, environ['wsgi.input'])
            with FunctionTrace(transaction.thread_id, name='Application', func_name=callable_name(wrapped)):
                result = wrapped(*args, **kwargs)
        except:
            transaction.__exit__(*sys.exc_info())
            raise

        transaction.__exit__(None, None, None)
        return result

    return FuncWrapper(wrapped, _pam_wsgi_application_wrapper_)