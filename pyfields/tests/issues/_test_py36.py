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


def test_issue_73():
    class Foo:
        bar: 'Foo' = field(check_type=True, nonable=True)
    return Foo


class A:
    bar: 'B' = field(check_type=True, nonable=True)

class B:
    bar: 'A' = field(check_type=True, nonable=True)


def test_issue_73_cross_ref():
    # note: we have to define the classes outside the function for the cross-ref to work
    # indeed typing.get_type_hints() will only access the globals of the defining module
    return A, B
