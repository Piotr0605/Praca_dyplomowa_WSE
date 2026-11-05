"""Blokada przed usunięciem bazy, która nie jest testowa."""

import pytest
from sqlalchemy import make_url

from tests.db_helpers import drop_database, recreate_database


@pytest.mark.parametrize("operacja", [recreate_database, drop_database])
def test_baza_deweloperska_nie_moze_zostac_usunieta(operacja) -> None:
    with pytest.raises(ValueError, match="nie jest testowa"):
        operacja(make_url("postgresql+psycopg://u:p@localhost/finanse"))
