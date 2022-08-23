import sys
sys.path.insert(1, './')

from jen import *
from cmath import nan
import random
import pathlib
import pytest


def test_underscore_write_raise_error_case_1():
    error_msg = "'Trying to subscribe \"a\" but parent is not a list or dict.'"

    with pytest.raises(KeyError) as k:
        gb._write(None, ["a"], None)
    assert str(k.value) == error_msg

    with pytest.raises(KeyError):
        gb._write(1, ["a"], None)
    assert str(k.value) == error_msg

    with pytest.raises(KeyError):
        gb._write(2.3, ["a"], None)
    assert str(k.value) == error_msg

    with pytest.raises(KeyError):
        gb._write("1", ["a"], None)
    assert str(k.value) == error_msg

    with pytest.raises(KeyError):
        gb._write(nan, ["a"], None)
    assert str(k.value) == error_msg

    with pytest.raises(KeyError):
        gb._write(lambda: 1, ["a"], None)
    assert str(k.value) == error_msg


def test_underscore_write_raise_error_case_2():
    error_msg = "'The parent is a list but key \"%s\" is not a valid index.'"

    with pytest.raises(KeyError) as k:
        gb._write([], [""], None)
    assert str(k.value) == error_msg % ""

    with pytest.raises(KeyError) as k:
        gb._write([], ["a"], None)
    assert str(k.value) == error_msg % "a"

    with pytest.raises(KeyError) as k:
        gb._write([], ["3.14"], None)
    assert str(k.value) == error_msg % "3.14"

    with pytest.raises(KeyError) as k:
        gb._write([], ["-1"], None)
    assert str(k.value) == error_msg % "-1"

    with pytest.raises(KeyError) as k:
        gb._write([], ["+1"], None)
    assert str(k.value) == error_msg % "+1"

    with pytest.raises(KeyError) as k:
        gb._write([], ["00"], None)
    assert str(k.value) == error_msg % "00"

    with pytest.raises(KeyError) as k:
        gb._write([], ["01"], None)
    assert str(k.value) == error_msg % "01"


def test_underscore_write_set_value_level_1():
    parent = []
    gb._write(parent, ["0"], 123.45)
    assert parent == [123.45]

    parent = [456]
    gb._write(parent, ["0"], 123.45)
    assert parent == [123.45]

    parent = [456, 789]
    gb._write(parent, ["0"], 123.45)
    assert parent == [123.45, 789]

    parent = [456, 789]
    gb._write(parent, ["1"], 123.45)
    assert parent == [456, 123.45]

    parent = []
    gb._write(parent, ["0"], 123.45)
    assert parent == [123.45]

    parent = []
    gb._write(parent, ["1"], 123.45)
    assert parent == [None, 123.45]

    parent = []
    gb._write(parent, ["3"], 123.45)
    assert parent == [None, None, None, 123.45]

    parent = [456, 789]
    gb._write(parent, ["3"], 123.45)
    assert parent == [456, 789, None, 123.45]

    parent = {}
    gb._write(parent, ["3"], 123.45)
    assert parent == {"3": 123.45}

    parent = {}
    gb._write(parent, ["test"], 123.45)
    assert parent == {"test": 123.45}

    parent = {"test": 456}
    gb._write(parent, ["test"], 123.45)
    assert parent == {"test": 123.45}

    parent = {"": None}
    gb._write(parent, [""], 123.45)
    assert parent == {"": 123.45}

    parent = {"test1": 789}
    gb._write(parent, ["test"], 123.45)
    assert parent == {"test": 123.45, "test1": 789}


def test_underscore_write_set_value_level_2():
    parent = []
    gb._write(parent, ["0", "e"], 123.45)
    assert parent == [{"e": 123.45}]

    parent = []
    gb._write(parent, ["0", "0"], 123.45)
    assert parent == [[123.45]]

    parent = []
    gb._write(parent, ["3", "4"], 123.45)
    assert parent == [None, None, None, [None, None, None, None, 123.45]]

    parent = {}
    gb._write(parent, ["3", "e"], 123.45)
    assert parent == {"3": {"e": 123.45}}

    parent = {}
    gb._write(parent, ["3", "4"], 123.45)
    assert parent == {"3": [None, None, None, None, 123.45]}

    parent = {}
    gb._write(parent, ["test", "test1"], 123.45)
    assert parent == {"test": {"test1": 123.45}}


def test_write_no_wildcard_allowed():
    with pytest.raises(KeyError) as k:
        gb.write("*", None)

    with pytest.raises(KeyError) as k:
        gb.write("any*", None)
    
    with pytest.raises(KeyError) as k:
        gb.write("any*any", None)


def test_write_no_repeat():
    test = []
    gb.share = {"test": test}
    gb.write("test", [])
    assert gb.share["test"] is test


def test_write_no_cache_pollution():
    test = []
    gb.share = {"test": test}
    with pytest.raises(ValueError) as k:
        gb.write("test", test)


def test_read_write_clone_function():
    test = {"test": 123.45}
    gb.write("", test)
    assert gb.share is test
    assert gb.read("") is test
    assert gb.clone("") is not test

    test = {"test": 123.45}
    gb.write("something", test)
    assert gb.share["something"] is test
    assert gb.read("something") is test
    assert gb.clone("something") is not test


def test_yml_read():
    gb.init(pathlib.Path(__file__).parent.parent / "initial.yml")

    with pytest.raises(BaseException):
        gb.init(pathlib.Path(__file__).parent / "not_found.yml")

    with pytest.raises(BaseException):
        gb.init(pathlib.Path(__file__).parent / "test.yml")
