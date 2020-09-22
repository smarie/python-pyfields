import sys

import pytest

from pyfields import get_fields


@pytest.mark.skipif(sys.version_info < (3, 6), reason="Annotations not supported in python < 3.6")
def test_issue_74():
    """test associated with the non-issue 74"""
    from ._test_py36 import test_issue_74
    City = test_issue_74()
    c = City(name=None)
    assert c.name is None
    assert c.buildings == []


def test_issue_76():
    """ issue 76 is fixed """
    from ._test_py36 import test_issue_76
    Foo = test_issue_76()
    assert [f.name for f in get_fields(Foo)] == ['c', 'b']
