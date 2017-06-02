import pytest

from pamagent.transaction import Transaction


def test_transaction():
    tr = Transaction(enabled=True)
    with tr:
        assert tr.enabled
        print(tr.start_time)
        assert 0.0 == tr.start_time


def test_transaction_disabled():
    tr = Transaction()
    with tr:
        assert tr.enabled is False
        assert tr.start_time == 0.0


def test_duplicate_transaction():
    tr = Transaction(enabled=True)
    tr1 = Transaction(enabled=True)
    with tr:
        with pytest.raises(RuntimeError) as exc:
            with tr1:
                print("1")
        assert "Transaction already active" in str(exc.value)


def test_drop_transaction():
    tr = Transaction(enabled=True)
    tr1 = Transaction(enabled=True)
    with tr:
        assert tr.enabled
        assert 0.0 == tr1.start_time
    with tr1:
        assert tr1.enabled
        assert 0.0 == tr1.start_time
    tr1.enabled = True
    with pytest.raises(RuntimeError) as exc:
        tr1.__exit__(None, None, None)
        assert "No active transaction" in str(exc.value)
