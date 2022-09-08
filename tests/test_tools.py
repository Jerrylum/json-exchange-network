import sys
sys.path.insert(1, './')

from jen import *
import random
import pytest


def test_clock_busy_wait():
    for i in range(1, 1001):
        c = Clock(frequency=i, busyWait=True)
        c.spin()
    for i in range(1, 1001):
        c = Clock(frequency=i)
        c.spin()


def test_tps_counter():
    for i in range(0, 1001):
        t = TpsCounter()
        for _ in range(i):
            t.tick()
        t._last_sec_timestamp -= 1
        t.tick()

        assert t.tps() == i


def test_diff():
    d = Diff(123, "a", "b")
    e = Diff(uuid=123, path="c", change="d")
    f = Diff(uuid=124, path="a", change="b")
    assert d == Diff(uuid=123, path="a", change="b")
    assert d == e
    assert d != f
    assert d != True
    assert d.diff_id == 123
    assert d.path == "a"
    assert d.change == "b"
    assert [d] == [e]
    assert [d] != [f]
    assert hash(d) == hash(e)

    g = Diff.build(path="a", change="b")
    assert g.path == "a"
    assert g.change == "b"


def test_diff_match():
    # match watcher path check

    diff0 = Diff(123, "", "b")
    assert diff0.match("b") == False
    assert diff0.match("*")
    assert diff0.match("")
    assert diff0.match("a") == False
    assert diff0.match("a.") == False
    assert diff0.match("a*") == False
    assert diff0.match("a.*") == False
    assert diff0.match("a.b") == False
    assert diff0.match("a.b.") == False
    assert diff0.match("a.b*") == False
    assert diff0.match("a.b.*") == False

    diff1 = Diff(123, "a", "b")
    assert diff1.match("b") == False
    assert diff1.match("*")
    assert diff1.match("") == False
    assert diff1.match("a")
    assert diff1.match("a.") == False
    assert diff1.match("a*")
    assert diff1.match("a.*") == False
    assert diff1.match("a.b") == False
    assert diff1.match("a.b.") == False
    assert diff1.match("a.b*") == False
    assert diff1.match("a.b.*") == False

    diff2 = Diff(123, "a.", "b")
    assert diff2.match("b") == False
    assert diff2.match("*")
    assert diff2.match("") == False
    assert diff2.match("a") == False
    assert diff2.match("a.")
    assert diff2.match("a*")  # suspicious
    assert diff2.match("a.*")
    assert diff2.match("a.b") == False
    assert diff2.match("a.b.") == False
    assert diff2.match("a.b*") == False
    assert diff2.match("a.b.*") == False

    diff3 = Diff(123, "a.b", "b")
    assert diff3.match("b") == False
    assert diff3.match("*")
    assert diff3.match("") == False
    assert diff3.match("a") == False
    assert diff3.match("a.") == False
    assert diff3.match("a*")
    assert diff3.match("a.*")
    assert diff3.match("a.b")
    assert diff3.match("a.b.") == False
    assert diff3.match("a.b*")
    assert diff3.match("a.b.*") == False

    diff4 = Diff(123, "a.b.c", "b")
    assert diff4.match("b") == False
    assert diff4.match("*")
    assert diff4.match("") == False
    assert diff4.match("a") == False
    assert diff4.match("a.") == False
    assert diff4.match("a*")
    assert diff4.match("a.*")
    assert diff4.match("a.b") == False
    assert diff4.match("a.b.") == False
    assert diff4.match("a.b*")
    assert diff4.match("a.b.*")


def test_diff_related():
    d = Diff(123, "a", "b")
    e = Diff(123, "a", "b")

    assert d.related(e.path)
    assert e.related(d.path)

    f = Diff(123, "ab", "b")
    g = Diff(123, "a", "c")

    assert f.related(g.path)
    assert g.related(f.path)
