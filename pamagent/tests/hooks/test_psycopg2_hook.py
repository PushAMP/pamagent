import pytest

from pamagent.hooks.psycopg2_hook import instance_info


@pytest.mark.parametrize("connected_params,expected", [
    ({'dsn': "postgres://USER:PASSWORD@host_name:3456/database_name"}, ('host_name', '3456', 'database_name')),
    ({'dsn': "postgres://USER:PASSWORD@host_name/database_name"}, ('host_name', None, 'database_name')),
    ({'host': "host_name", "port": 5431, "database": "rest_db"}, ('host_name', '5431', 'rest_db')),
    ({'host': "host_name", "database": "rest_db"}, ('host_name', None, 'rest_db')),
])
def test__instance_info(connected_params, expected):
    info = instance_info((), connected_params)
    assert info == expected
