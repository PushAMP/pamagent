import logging

import _thread

from pamagent import pamagent_core

_logger = logging.getLogger(__name__)


def current_thread_id():
    """
    Returns the thread ID for the caller.
    """
    return _thread.get_ident()


def current_transaction():
    """
    Return the transaction object if one exists for the currently executing thread.
    """
    return pamagent_core.get_transaction(_thread.get_ident())


def save_transaction(transaction):
    """
    Saves the specified transaction away under the thread ID of the current executing thread.
    """
    res = pamagent_core.set_transaction(id=transaction.thread_id, transaction=transaction.name, path=transaction.path)
    if not res:
        raise RuntimeError('Transaction already active')


def drop_transaction(transaction):
    """
    Drops the specified transaction, validating that it is actually saved away under the current executing thread.
    """

    res = pamagent_core.drop_transaction(id=transaction.thread_id)
    if not res:
        raise RuntimeError('No active transaction')


def set_transaction_name(name):
    """
    Set transaction path by current thread ID
    """
    res = pamagent_core.set_transaction_path(id=current_thread_id(), path=name)
    if not res:
        raise RuntimeError('No active transaction')


def get_start_time(transaction):
    return pamagent_core.get_transaction_start_time(id=transaction.thread_id)


def get_end_time(transaction):
    return pamagent_core.get_transaction_end_time(id=transaction.thread_id)
