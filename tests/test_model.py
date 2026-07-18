from acikpoz.model import Poz


def test_is_priced() -> None:
    assert Poz("15.100.1003", "taş", "m³", 54.88).is_priced
    assert not Poz("15.100.1003", "taş").is_priced  # no price -> gap, not zero


def test_roundtrip() -> None:
    p = Poz("15.100.1003", "1 m³ taş", "m³", 54.88)
    assert Poz.from_dict(p.to_dict()) == p


def test_group_header_roundtrip() -> None:
    p = Poz("25.110.1000", "EVİYELER:", is_group_header=True)
    back = Poz.from_dict(p.to_dict())
    assert back.is_group_header
    assert back.fiyat is None


def test_grup() -> None:
    assert Poz("15.100.1003", "taş").grup == "15"
    assert Poz("25.110.1000", "hela:").grup == "25"


def test_to_dict_includes_grup() -> None:
    d = Poz("15.100.1003", "taş", "m³", 54.88).to_dict()
    assert d["grup"] == "15"
