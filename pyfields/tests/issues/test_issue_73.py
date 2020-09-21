import sys

import pytest
from pyfields import FieldTypeError


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not supported in python < 3.6")
@pytest.mark.parametrize('str_hint', [False, True], ids="str_hint={}".format)
@pytest.mark.parametrize('fix_in_class_field', [False, True], ids="fix_in_class_field={}".format)
def test_self_referenced_class(str_hint, fix_in_class_field):
    """Fix https://github.com/smarie/python-pyfields/issues/73 """
    if str_hint:
        # this is the old behaviour that happens even when PEP563 is not enabled at the top of the module
        from ._test_py36 import test_issue_73
        Foo = test_issue_73()
    else:
        # this is the new behaviour that happens when PEP563 is enabled at the top of the module
        from ._test_py36_pep563 import test_issue_73
        Foo = test_issue_73()

    if fix_in_class_field:
        # this will read the class fields, and the fix will happen during reading
        assert Foo.bar.type_hint is Foo

    # if the fix was not done before, it is done when the field is first used
    f = Foo()
    with pytest.raises(FieldTypeError):
        f.bar = 1

    f.bar = f
    assert f.bar is f

    if not fix_in_class_field:
        # we can optionally check this now, but the mere fact that the above worked is already a proof
        assert Foo.bar.type_hint is Foo


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not supported in python < 3.6")
@pytest.mark.parametrize('str_hint', [False, True], ids="str_hint={}".format)
@pytest.mark.parametrize('fix_in_class_field', [False, True], ids="fix_in_class_field={}".format)
def test_cross_referenced_class(str_hint, fix_in_class_field):
    if str_hint:
        from ._test_py36 import test_issue_73_cross_ref
        A, B = test_issue_73_cross_ref()
    else:
        from ._test_py36_pep563 import test_issue_73_cross_ref
        A, B = test_issue_73_cross_ref()

    if fix_in_class_field:
        # this will read the class fields, and the fix will happen during reading
        assert A.bar.type_hint is B
        assert B.bar.type_hint is A

    # if the fix was not done before, it is done when the field is first used
    a = A()
    with pytest.raises(FieldTypeError):
        a.bar = 1

    b = B()
    a.bar = b
    b.bar = a
    assert a.bar is b
    assert b.bar is a

    if not fix_in_class_field:
        # we can optionally check this now, but the mere fact that the above worked is already a proof
        assert A.bar.type_hint is B
        assert B.bar.type_hint is A
