import cgi
import logging
import time
import urllib.parse

from pamagent import pamagent_core

from .transaction_cache import save_transaction, drop_transaction, current_thread_id, get_start_time, get_end_time

_logger = logging.getLogger(__name__)


class Transaction(object):
    STATE_PENDING = 0
    STATE_RUNNING = 1
    STATE_STOPPED = 2

    def __init__(self, enabled=None):
        self._state = self.STATE_PENDING
        self.enabled = False
        self.thread_id = current_thread_id()
        self._transaction_id = id(self)
        self._name = "Trans"
        self.stopped = False
        self._path = ""
        if enabled:
            self.enabled = True

    @property
    def start_time(self):
        return get_start_time(self)

    @property
    def end_time(self):
        return get_end_time(self)

    def __del__(self):
        if self._state == self.STATE_RUNNING:
            self.__exit__(None, None, None)

    def save_transaction(self):
        save_transaction(self)

    def drop_transaction(self):
        drop_transaction(self)

    def __enter__(self):
        assert (self._state == self.STATE_PENDING)
        if not self.enabled:
            return self
        self._state = self.STATE_RUNNING
        try:
            self.save_transaction()
        except Exception:
            self._state = self.STATE_PENDING
            self.enabled = False
            raise

        pamagent_core.push_current(self.thread_id, id(self), time.time())
        return self

    def __exit__(self, exc, value, tb):
        if not self.enabled:
            return

        self._state = self.STATE_STOPPED
        if self._transaction_id != id(self):
            return

        try:
            print(self.end_time)
            pamagent_core.pop_current(self.thread_id, id(self), time.time())
            self.drop_transaction()
        except Exception:
            _logger.exception('Fail to drop transaction.')
            raise

        # if not self.stopped:
        #     self.end_time = time.time()
        # duration = self.end_time - self.start_time
        # if not self._cpu_user_time_end:
        #     self._cpu_user_time_end = os.times()[0]
        #
        # if duration and self._cpu_user_time_end:
        #     self._cpu_user_time_value = (self._cpu_user_time_end - self._cpu_user_time_start)
        #
        # response_time = duration
        # root = self._node_stack.pop()
        #
        # children = root.children
        # exclusive = duration + root.exclusive
        # self.total_time = duration
        # node = TransactionNode(
        #     base_name=self._name,
        #     start_time=self.start_time,
        #     end_time=self.end_time,
        #     total_time=self.total_time,
        #     duration=duration,
        #     exclusive=exclusive,
        #     children=tuple(children),
        #     guid=self.guid,
        #     cpu_time=self._cpu_user_time_value,
        #     response_time=response_time,
        #     path=self.path,
        # )

        self.enabled = False
        # print(node)

    @property
    def state(self):
        return self._state

    @property
    def type(self):
        transaction_type = 'WebTransaction'
        return transaction_type

    def set_transaction_path(self, path):
        self._path = path
        pamagent_core.set_transaction_path(self.thread_id, path)

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name


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

        try:
            self._port = int(environ.get['SERVER_PORT'])
        except Exception:
            pass

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

            self.save_transaction()

            if self._request_uri is None:
                self._request_uri = self._path
        else:
            if self._request_uri is not None:
                self._path = self._request_uri
                self.save_transaction()

        now = time.time()

        def _parse_time_stamp(time_stamp):
            """
            Converts time_stamp to seconds. Input can be microseconds, milliseconds or seconds
            """
            for divisor in (1000000.0, 1000.0, 1.0):
                converted_time = time_stamp / divisor
                if converted_time > now:
                    return 0.0
            return 0.0

        queue_time_headers = ('HTTP_X_REQUEST_START', 'HTTP_X_QUEUE_START', 'mod_wsgi.request_start',
                              'mod_wsgi.queue_start')
        for queue_time_header in queue_time_headers:
            value = environ.get(queue_time_header, None)
            try:
                if value.startswith('t='):
                    try:
                        self.queue_start = _parse_time_stamp(float(value[2:]))
                    except Exception:
                        pass
                else:
                    try:
                        self.queue_start = _parse_time_stamp(float(value))
                    except Exception:
                        pass
            except Exception:
                pass

            if self.queue_start > 0.0:
                break

        qs = environ.get('QUERY_STRING', None)

        if qs:
            params = urllib.parse.parse_qs(qs, keep_blank_values=True)
            self._request_params.update(params)
        self.url_name = 'unknown'
        self.view_name = 'unknown'
