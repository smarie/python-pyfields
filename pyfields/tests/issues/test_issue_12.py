import inspect

from pyfields import field
from pyfields.core import NativeField


def test_class_access_and_autocomplete():
    """ test that https://github.com/smarie/python-pyfields/issues/12 is resolved """
    class Foo:
        a = field(type_hint=int, default=1)

    assert Foo.a.name == 'a'
    assert isinstance(Foo.a, NativeField)
    assert dict(inspect.getmembers(Foo))['a'] == Foo.a

    f = Foo()
    assert f.a == 1

    Foo.a = 5
