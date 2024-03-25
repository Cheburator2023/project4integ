from app.utils import remove_cyrillic
import pytest


@pytest.mark.parametrize(
    "some_string",
    "expected_value",
    [
        ("hello", "hello"),
        ("Привет Мир", "Privet Mir"),
        ("Model один", "Model odin"),
        ("3123333312", "3123333312"),
        ("!@333lklffjl", "!@333lklffjl"),
        ("Some тест string with 123!@#", "Some test string with 123!@#"),
    ],
)
def test_remove_cyrillic(some_string, expected_value):
    assert remove_cyrillic(some_string) == expected_value
