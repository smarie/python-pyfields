#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys

import pytest

from pyfields import autofields, field, FieldTypeError, Field


@pytest.mark.parametrize("with_type_hints", [False, True],
                         ids="with_type_hints={}".format)
def test_autofields_basic(with_type_hints):
    """tests that basic functionality of @autofields is ok """

    if with_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip("Type annotations are not supported in python < 3.6")

        from ._test_py36 import _test_autofields
        Foo = _test_autofields()

        # test it
        assert isinstance(Foo.__dict__['barcls'], Field)
        assert isinstance(Foo.__dict__['barfunc'], Field)
        assert not isinstance(Foo.__dict__['fct'], Field)
        assert not isinstance(Foo.__dict__['cls'], Field)

        f = Foo(foo=1, barbar='yo', barfunc=lambda x: 2, barcls=str)
        with pytest.raises(FieldTypeError):
            f.foo = 'ha'

        assert f.bar == 0
        assert f.fct() == 1
        assert f.barfunc(1) == 2
        assert f.barcls == str

    else:
        # retrocompatbility mode for python < 3.6
        # note: we also use this opportunity to test with parenthesis
        @autofields()
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
