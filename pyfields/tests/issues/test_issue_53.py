#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

from pyfields import field, init_fields, get_field


def test_issue_53():

    class A(object):
        a = field(str, check_type=True)

        @init_fields()
        def __init__(self):
            pass

    class B(A):
        b = field(str, check_type=True)

        @init_fields()
        def __init__(self):
            super(B, self).__init__(a=self.a)

    # note that with the issue, this was raising an exception
    print(B('a', 'b'))
