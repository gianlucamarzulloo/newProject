import time

import pytest
import sympy as sp

from englab.core import sandbox
from englab.core.parsing import ParseError, parse, parse_number, x


@pytest.mark.parametrize("text, expected", [
    ("x^2", x**2),
    ("2x", 2 * x),
    ("sen(x)", sp.sin(x)),
    ("tg(x)", sp.tan(x)),
    ("arctg(x)", sp.atan(x)),
    ("ln(x)", sp.log(x)),
    ("log(x)", sp.log(x)),
    ("e^x", sp.exp(x)),
    ("3sen(x)cos(x)", 3 * sp.sin(x) * sp.cos(x)),
    ("|x|", sp.Abs(x)),
    ("2,5x", sp.Float(2.5) * x),
    ("π", sp.pi),
    ("x²", x**2),
])
def test_parse_italian_notation(text, expected):
    assert sp.simplify(parse(text) - expected) == 0


@pytest.mark.parametrize("payload", [
    "__import__('os').system('ls')",
    "x.__class__",
    "lambda: 1",
    "open('/etc/passwd')",
    "eval(x)",
    "xy",
    "x" * 400,
    "",
    "[1, 2]",
])
def test_parse_rejects_unsafe_or_invalid(payload):
    with pytest.raises(ParseError):
        parse(payload)


def test_parse_number():
    assert parse_number("1/2") == 0.5
    assert parse_number("pi") == pytest.approx(3.14159265)
    with pytest.raises(ParseError):
        parse_number("x")


def test_sandbox_returns_result():
    assert sandbox.run(sum, [1, 2, 3]) == 6


def test_sandbox_kills_slow_computation():
    start = time.monotonic()
    with pytest.raises(sandbox.ComputationTimeout):
        sandbox.run(time.sleep, 30, timeout=1)
    assert time.monotonic() - start < 5


def test_sandbox_propagates_input_errors():
    with pytest.raises(ParseError):
        sandbox.run(parse, "import os")
