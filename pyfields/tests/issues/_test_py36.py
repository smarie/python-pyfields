#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
from pyfields import field, init_fields


def test_issue_51():
    class A:
        f: str = field(check_type=True, default=None, nonable=True)

        @init_fields
        def __init__(self):
            pass

    return A
