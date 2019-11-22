#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys

import pytest


@pytest.mark.skipif(sys.version_info < (3, 6), reason="member type hints not supported in python < 3.6")
def test_issue_51():
    from ._test_py36 import test_issue_51
    A = test_issue_51()
    a = A()
