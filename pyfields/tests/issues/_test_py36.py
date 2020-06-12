#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
from pyfields import field, init_fields, autofields


def test_issue_51():
    class A:
        f: str = field(check_type=True, default=None, nonable=True)

        @init_fields
        def __init__(self):
            pass

    return A


def test_issue_67():
    @autofields
    class Frog:
        another: int = 1

        @property
        def balh(self):
            print('asd')

    return Frog
