from tools.calculator import calculate


def test_basic_arithmetic():
    assert calculate("2 + 2") == "4"
    assert calculate("10 - 3") == "7"
    assert calculate("4 * 5") == "20"
    assert calculate("20 / 4") == "5.0"


def test_advanced_operations():
    assert calculate("2 ** 10") == "1024"
    assert calculate("17 % 5") == "2"
    assert calculate("10 // 3") == "3"


def test_constants():
    assert float(calculate("pi")) == 3.141592653589793
    assert float(calculate("e")) == 2.718281828459045


def test_functions():
    assert calculate("abs(-5)") == "5"
    assert calculate("round(3.7)") == "4"
    assert calculate("int(3.9)") == "3"
    assert calculate("min(1, 5, 3)") == "1"
    assert calculate("max(1, 5, 3)") == "5"
    # sum is not available (needs an iterable, not varargs)


def test_complex_expressions():
    assert calculate("pi * 5 ** 2") == "78.53981633974483"
    assert calculate("abs(-10) + round(3.7)") == "14"
    assert calculate("2 * (3 + 4)") == "14"


def test_invalid_input():
    result = calculate("__import__('os')")
    assert result.startswith("Error")


def test_undefined_variable():
    result = calculate("x + 1")
    assert result.startswith("Error")
