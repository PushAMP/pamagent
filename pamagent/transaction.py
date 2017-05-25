import logging
import os
import random
import time
from collections import namedtuple

from .transaction_cache import save_transaction, drop_transaction, current_thread_id
from .agent import TimeTrace

_logger = logging.getLogger(__name__)

_TransactionNode = namedtuple('_TransactionNode',
                              ['base_name', 'start_time', 'end_time', 'total_time', 'duration', 'exclusive',
                               'children', 'guid', 'cpu_time', 'response_time', 'path']
                              )
TimeMetric = namedtuple('TimeMetric',
                        ['name', 'scope', 'duration', 'exclusive'])


RootNode = namedtuple('RootNode',
                      ['start_time', 'empty0', 'empty1', 'root', 'attributes'])

from pamagent import pamagent_core
def node_start_time(root, node):
    return int((node.start_time - root.start_time) * 1000.0)


def node_end_time(root, node):
    return int((node.end_time - root.start_time) * 1000.0)


def root_start_time(root):
    return root.start_time / 1000.0


class TransactionNode(_TransactionNode):
    def __hash__(self):
        return id(self)

    def time_metrics(self, stats):

        if not self.base_name:
            return

        yield TimeMetric(name=self.path, scope='', duration=self.response_time, exclusive=self.exclusive)

        for child in self.children:
            for metric in child.time_metrics(stats, self, self):
                yield metric

    def trace_node(self, stats, root, connections):

        name = self.path

        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)

        root.trace_node_count += 1

        children = []

        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break
            children.append(child.trace_node(stats, root, connections))

        params = {}

        return TraceNode(start_time=start_time, end_time=end_time, name=name, params=params, children=children,
                         label=None)

    def transaction_trace(self, stats, limit, connections):

        self.trace_node_count = 0
        self.trace_node_limit = limit

        start_time = root_start_time(self)

        trace_node = self.trace_node(stats, self, connections)

        root = TraceNode(start_time=trace_node.start_time, end_time=trace_node.end_time, name='ROOT', params={},
                         children=[trace_node], label=None)

        return RootNode(start_time=start_time, empty0={}, empty1={}, root=root)


class Transaction(object):
    STATE_PENDING = 0
    STATE_RUNNING = 1
    STATE_STOPPED = 2

    def __init__(self, enabled=None):
        self._state = self.STATE_PENDING
        self.enabled = False
        self.thread_id = current_thread_id()
        self._transaction_id = id(self)
        self._name = None
        self._node_stack = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.total_time = None
        self.stopped = False
        self._cpu_user_time_start = None
        self._cpu_user_time_end = None
        self._cpu_user_time_value = 0.0
        self.guid = '%016x' % random.getrandbits(64)
        self._path = None

        if enabled:
            self.enabled = True

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

        self.start_time = time.time()
        self._cpu_user_time_start = os.times()[0]
        pamagent_core.push_current(self.thread_id, id(self), self.start_time)
        self._node_stack.append(TimeTrace(None))
        return self

    def __exit__(self, exc, value, tb):
        if not self.enabled:
            return

        self._state = self.STATE_STOPPED
        if self._transaction_id != id(self):
            return

        try:
            self.drop_transaction()
        except Exception:
            _logger.exception('Fail to drop transaction.')
            raise

        if not self.stopped:
            self.end_time = time.time()
        duration = self.end_time - self.start_time
        if not self._cpu_user_time_end:
            self._cpu_user_time_end = os.times()[0]

        if duration and self._cpu_user_time_end:
            self._cpu_user_time_value = (self._cpu_user_time_end - self._cpu_user_time_start)

        response_time = duration
        root = self._node_stack.pop()
        children = root.children
        exclusive = duration + root.exclusive
        self.total_time = duration
        node = TransactionNode(
            base_name=self._name,
            start_time=self.start_time,
            end_time=self.end_time,
            total_time=self.total_time,
            duration=duration,
            exclusive=exclusive,
            children=tuple(children),
            guid=self.guid,
            cpu_time=self._cpu_user_time_value,
            response_time=response_time,
            path=self.path,
        )

        self.enabled = False
        print(node)

    @property
    def state(self):
        return self._state

    @property
    def type(self):
        transaction_type = 'WebTransaction'
        return transaction_type

    def set_transaction_path(self, path):
        self._path = path

    @property
    def path(self):
        return self._path
