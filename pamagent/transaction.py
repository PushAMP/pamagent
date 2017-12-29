import logging
import time

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
        self._read_start = 0.0
        self._read_end = 0.0
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
        if self._state != self.STATE_PENDING:
            RuntimeError("Transaction state invalid")
        if not self.enabled:
            return self
        self._state = self.STATE_RUNNING
        try:
            self.save_transaction()
        except Exception:
            self._state = self.STATE_PENDING
            self.enabled = False
            raise

        pamagent_core.push_current(self.thread_id, id(self), time.time(), None)
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
        self.enabled = False

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

    def dump(self):
        _logger.warning("Please use this method only for debug")
        return pamagent_core.dump_transaction(self.thread_id)


def dump_current_transaction():
    import json
    _logger.warning("Please use this method only for debug")
    p = pamagent_core.dump_transaction(current_thread_id())
    if p:
        return json.loads(p)
