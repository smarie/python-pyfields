from __future__ import annotations  # python 3.10 behaviour see https://www.python.org/dev/peps/pep-0563/
from pyfields import field


def test_issue_73():
    class Foo:
        bar: Foo = field(check_type=True, nonable=True)
    return Foo


class A:
    bar: B = field(check_type=True, nonable=True)

class B:
    bar: A = field(check_type=True, nonable=True)


def test_issue_73_cross_ref():
    # note: we have to define the classes outside the function for the cross-ref to work
    # indeed typing.get_type_hints() will only access the globals of the defining module
    return A, B
