import sys

import pytest

try:
    from abc import ABC
except ImportError:
    from abc import ABCMeta

    class ABC:
        __metaclass__ = ABCMeta


from pyfields import autofields, field, copy_value, autoclass


@pytest.mark.skipif(sys.version_info < (3,), reason="This test does not yet reproduce the exception in python 2")
@pytest.mark.parametrize("auto,deep", [(False, False), (False, True), (True, None)])
def test_issue_deepcopy_autofields(auto, deep):
    """Make sure that """

    class NotCopiable(object):
        def __deepcopy__(self, memodict={}):
            raise NotImplementedError()

        def __copy__(self):
            raise NotImplementedError()

    default_value = NotCopiable()

    if auto:
        with pytest.raises(ValueError) as exc_info:
            @autofields
            class Foo:
                a = default_value
        assert str(exc_info.value).startswith("The provided default value for field 'a'=%r can not be deep-copied"
                                              % (default_value, ))
    else:
        with pytest.raises(ValueError) as exc_info:
            class Foo:
                a = field(default_factory=copy_value(default_value, deep=deep))

        extra = "deep-" if deep else ""
        assert str(exc_info.value).startswith("The provided default value %r can not be %scopied"
                                              % (default_value, extra))


def test_issue_84_autofields():
    """Make sure that the _abc_impl field from ABC is excluded automatically"""

    @autofields
    class Foo(ABC):
        a = 0

    g = Foo()
    assert g.a == 0

    if sys.version_info < (3, 7):
        # errors below wont be raised anyway
        return

    with pytest.raises(ValueError) as exc_info:
        @autofields(exclude=())
        class Foo(ABC):
            a = 0

    assert str(exc_info.value).startswith("The provided default value for field '_abc_impl'=")


def test_issue_84_autoclass():
    """Make sure that the _abc_impl field from ABC is excluded automatically"""

    @autoclass
    class Foo(ABC):
        a = 0

    f = Foo()
    assert str(f) == "Foo(a=0)"

    if sys.version_info < (3, 7):
        # errors below wont be raised anyway
        return

    with pytest.raises(ValueError) as exc_info:
        @autoclass(af_exclude=())
        class Foo(ABC):
            a = 0

    assert str(exc_info.value).startswith("The provided default value for field '_abc_impl'=")
