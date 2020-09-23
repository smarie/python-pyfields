#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys

import pytest

from pyfields import autofields, field, FieldTypeError, Field, get_fields, autoclass
from pyfields.core import NativeField


@pytest.mark.parametrize("with_type_hints,type_check", [(False, False), (True, False), (True, True)])
def test_autofields_basic(with_type_hints, type_check):
    """tests that basic functionality of @autofields is ok """

    if with_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip("Type annotations are not supported in python < 3.6")

        from ._test_py36 import _test_autofields
        Foo = _test_autofields(type_check)

        # test it
        assert isinstance(Foo.__dict__['barcls'], NativeField)
        assert isinstance(Foo.__dict__['barfunc'], Field)
        assert not isinstance(Foo.__dict__['fct'], Field)
        assert not isinstance(Foo.__dict__['cls'], Field)

        f = Foo(foo=1, barbar='yo', barfunc=lambda x: 2, barcls=str)
        if type_check:
            with pytest.raises(FieldTypeError):
                f.foo = 'ha'
        else:
            f.foo = 'ha'

        assert f.bar == 0
        assert f.fct() == 1
        assert f.barfunc(1) == 2
        assert f.barcls == str

    else:
        # retrocompatbility mode for python < 3.6
        # note: we also use this opportunity to test with parenthesis
        @autofields(check_types=type_check)
        class Foo(object):
            CONSTANT = 's'
            __a__ = 0

            foo = field()
            bar = 0     # type: int
            barcls = float
            barfunc = lambda x: x
            barbar = 0  # type: str

            class cls:
                pass

            def fct(self):
                return 1

        # test it
        assert isinstance(Foo.__dict__['barcls'], Field)
        assert isinstance(Foo.__dict__['barfunc'], Field)
        assert not isinstance(Foo.__dict__['fct'], Field)
        assert not isinstance(Foo.__dict__['cls'], Field)

        f = Foo(foo=1, barfunc=lambda x: 2, barcls=str)
        assert f.bar == 0
        assert f.fct() == 1
        assert f.barfunc(1) == 2
        assert f.barcls == str


def test_autofields_property_descriptors():
    """Checks that properties and descriptors are correctly ignored by autofields"""

    @autofields
    class Foo(object):
        foo = 1
        @property
        def bar(self):
            return 2

        class MyDesc():
            def __get__(self):
                return 1

        class MyDesc2():
            def __get__(self):
                return 0
            def __set__(self, instance, value):
                return

        m = MyDesc()
        p = MyDesc2()

    fields = get_fields(Foo)
    assert len(fields) == 1
    assert fields[0].name == 'foo'


@pytest.mark.skipif(sys.version_info < (3, 6), reason="Annotations not supported in python < 3.6")
def test_issue_74():
    """test associated with the non-issue 74"""
    from ._test_py36 import test_issue_74
    City = test_issue_74()
    c = City(name=None)
    assert c.name is None
    assert c.buildings == []


@pytest.mark.skipif(sys.version_info < (3, 6), reason="Annotations not supported in python < 3.6")
def test_issue_76():
    """ order issue 76 and 77 are fixed """
    from ._test_py36 import test_issue_76
    Foo = test_issue_76()
    assert [f.name for f in get_fields(Foo)] == ['c', 'b', 'a']


def test_issue_76_bis():
    """ another order issue with @autofields """

    @autofields
    class Foo(object):
        msg = field(type_hint=str)
        age = field(default=12, type_hint=int)

    assert [f.name for f in get_fields(Foo)] == ['msg', 'age']


def test_autoclass():
    """"""

    @autoclass
    class Foo(object):
        msg = field(type_hint=str)
        age = field(default=12, type_hint=int)

    f = Foo('hey')

    # str repr
    assert repr(f) == "Foo(msg='hey', age=12)"
    assert str(f) == repr(f)

    # dict and eq
    assert f.to_dict() == {'msg': 'hey', 'age': 12}

    same_dict = {'msg': 'hey', 'age': 12}
    assert f == same_dict
    assert f == Foo.from_dict(same_dict)

    diff_dict = {'age': 13, 'msg': 'hey'}
    assert f != diff_dict
    assert f != Foo.from_dict(diff_dict)

    assert f == Foo.from_dict(f.to_dict())

    # hash
    my_set = {f, f}
    assert my_set == {f}
    assert Foo('hey') in my_set
    my_set.remove(Foo('hey'))
    assert len(my_set) == 0

    # subclass A
    class Bar(Foo):
        pass

    b = Bar(msg='hey')
    assert str(b) == "Bar(msg='hey', age=12)"
    assert b == f
    assert f == b

    # hash
    my_set = {f, b}
    assert len(my_set) == 1  # yes: since the subclass does not define additional attributes.
    assert my_set == {f}

    # subclass B
    @autoclass
    class Bar2(Foo):
        ho = 3

    b2 = Bar2('hey')
    assert str(b2) == "Bar2(msg='hey', age=12, ho=3)"
    assert b2 != f
    assert f != b2

    # hash
    my_set = {b2, b}
    assert Bar2('hey') in my_set
