#  Authors: Sylvain MARIE <sylvain.marie@se.com>
#            + All contributors to <https://github.com/smarie/python-pyfields>
#
#  License: 3-clause BSD, <https://github.com/smarie/python-pyfields/blob/master/LICENSE>
import sys
import pytest


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not supported in python < 3.6")
def test_issue_81():
    """ See https://github.com/smarie/python-pyfields/issues/81 """
    from ._test_py36 import test_issue_81
    A, B = test_issue_81()

    # before the bug fix, B.a was mistakenyl recreated py autofields as an overridden mandatory field on B
    assert B.a.is_mandatory is False
    # this was therefore raising a "Missing required positional argument" error on the generated constructor
    B(b=3)
