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
