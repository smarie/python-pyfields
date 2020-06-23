import pytest

from pyfields import field, get_field_values, get_fields, copy_field
from pyfields.core import PY36


@pytest.mark.parametrize("a_first", [False, True], ids="ancestor_first={}".format)
@pytest.mark.parametrize("public_only", [False, True], ids="public_only={}".format)
def test_get_fields(a_first, public_only):
    class A(object):
        a = field()
        _d = field(default=5)

    class B(object):
        b = field()

    class C(B, A):
        a = field(default=None)
        c = field(default_factory=copy_field('b'))

    fields = get_fields(C, include_inherited=True, ancestors_first=a_first,
                        _auto_fix_fields=not PY36, public_only=public_only)
    field_names = [f.name for f in fields]
    if a_first:
        assert field_names == ['a', 'b', 'c'] if public_only else ['a', '_d', 'b', 'c']
    else:
        assert field_names == ['a', 'c', 'b'] if public_only else ['a', 'c', 'b', '_d']

    obj = C()
    obj.b = 2

    fields = get_field_values(obj, ancestors_first=a_first if a_first is not None else True, _auto_fix_fields=not PY36,
                              container_type=list, public_only=public_only)
    if a_first is None or a_first:
        assert fields == [('a', None), ('b', 2), ('c', 2)] if public_only else [('a', None), ('_d', 5), ('b', 2), ('c', 2)]
    else:
        assert fields == [('a', None), ('c', 2), ('b', 2)] if public_only else [('a', None), ('c', 2), ('b', 2), ('_d', 5)]
