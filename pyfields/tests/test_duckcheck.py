#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2020. All right reserved.
from makefun import with_signature

from pyfields import duckcheck


def test_duckcheck_methods_only():
    """Basic test that duckcheck works """

    class MyTemplate(object):
        @staticmethod
        def c(cls, **kwargs):
            pass

        def a(self, a):
            pass

        @classmethod
        def b(cls, **kwargs):
            pass

    @duckcheck
    @with_signature("(o: MyTemplate)")
    def foo(*args, **kwargs):
        pass

    class MyClass(object):
        @staticmethod
        def c(cls, toto):
            pass

        def a(self, aaaa):
            pass

        @classmethod
        def b(cls):
            pass

    foo(MyClass())
