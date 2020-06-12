#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2020. All right reserved.
import sys

import pytest

from pyfields import get_fields


@pytest.mark.skipif(sys.version_info < (3, 6), reason="member type hints not supported in python < 3.6")
def test_issue_67():
    from ._test_py36 import test_issue_67
    Frog = test_issue_67()

    assert len(get_fields(Frog)) == 1
    Frog()
