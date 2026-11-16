import pytest

from soclab import flags


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("SOC{abc}", True),
        ("  SOC{10.0.0.1}  ", True),
        ("soc{minusculas}", True),
        ("SOC{con espacio}", False),
        ("SOC{}", False),
        ("FLAG{abc}", False),
        ("SOC{a}b}", False),
        ("SOC{" + "a" * 201 + "}", False),
    ],
)
def test_format(value: str, valid: bool) -> None:
    assert flags.is_valid_format(value) is valid


def test_hash_roundtrip_case_insensitive() -> None:
    h = flags.hash_flag("SOC{Hola}")
    assert flags.is_valid_hash(h)
    assert flags.verify("soc{hola}", h)
    assert flags.verify("  SOC{HOLA} ", h)
    assert not flags.verify("SOC{adios}", h)


def test_hash_case_sensitive() -> None:
    h = flags.hash_flag("SOC{Hola}", case_sensitive=True)
    assert flags.verify("SOC{Hola}", h, case_sensitive=True)
    assert not flags.verify("SOC{hola}", h, case_sensitive=True)


def test_salt_makes_hashes_unique() -> None:
    assert flags.hash_flag("SOC{x1}") != flags.hash_flag("SOC{x1}")


def test_invalid_inputs() -> None:
    with pytest.raises(flags.FlagError):
        flags.hash_flag("sin formato")
    with pytest.raises(flags.FlagError):
        flags.hash_flag("SOC{a}", salt=b"corta")
    with pytest.raises(flags.FlagError):
        flags.verify("SOC{a}", "md5$abc")
    assert flags.verify("no es flag", flags.hash_flag("SOC{a}")) is False


def test_rejects_abusive_scrypt_params() -> None:
    evil = "scrypt$1048576$8$1$" + "0" * 32 + "$" + "0" * 64
    assert not flags.is_valid_hash(evil)
