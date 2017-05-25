from pamagent.agent import wrap_external_trace, instrument_requests_sessions, instrument_requests_api
from pamagent.transaction import Transaction

# import requests


def test_request_wrap():
    instrument_requests_sessions("requests")
    import requests
    print(dir(requests.Session.send))
    tr = Transaction(enabled=True)
    with tr:
        s = requests.session()
        s.get("http://ya.ru")
    print(tr)
