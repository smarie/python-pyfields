#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys

import pytest

from pyfields import field, init_fields, inject_fields, make_init, MandatoryFieldInitError, copy_field, get_fields
from pyfields.core import PY36


@pytest.mark.parametrize("native", [False, True], ids="native={}".format)
@pytest.mark.parametrize("init_type", ['inject_fields', 'make_init', 'make_init_with_postinit'],
                         ids="init_type={}".format)
@pytest.mark.parametrize("explicit_fields_list", [False, True], ids="explicit_list={}".format)
@pytest.mark.parametrize("py36_style_type_hints", [False, True], ids="py36_style_type_hints={}".format)
def test_init_all_methods(py36_style_type_hints, explicit_fields_list, init_type, native):
    """Test of @inject_fields with selected fields """
    if py36_style_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip()
            Wall = None
        else:
            # import the test that uses python  3.6 type annotations
            from ._test_py36 import _test_readme_constructor
            Wall = _test_readme_constructor(explicit_fields_list, init_type, native)
    else:
        if init_type == 'inject_fields':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)          # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str

                    @inject_fields(height, color)
                    def __init__(self, fields):
                        with pytest.raises(MandatoryFieldInitError):
                            print(self.height)
                        # initialize all fields received
                        fields.init(self)
                        print(self.height)
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)  # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str

                    @inject_fields
                    def __init__(self, fields):
                        with pytest.raises(MandatoryFieldInitError):
                            print(self.height)
                        # initialize all fields received
                        fields.init(self)
                        print(self.height)

        elif init_type == 'make_init':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)           # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str
                    __init__ = make_init(height, color)
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)  # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str
                    __init__ = make_init()

        elif init_type == 'make_init_with_postinit':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)  # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str
                    def post_init(self, foo='bar'):
                        self.height
                        print("post init man !")

                    __init__ = make_init(height, color, post_init_fun=post_init)
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.", native=native)           # type: int
                    color = field(default='white', doc="Color of the wall.", native=native)  # type: str
                    def post_init(self, foo='bar'):
                        self.height
                        print("post init man !")

                    __init__ = make_init(post_init_fun=post_init)
        else:
            raise ValueError(init_type)

    # first init
    w = Wall(height=12)
    if native:
        assert vars(w) == {'color': 'white', 'height': 12}
    else:
        assert vars(w) == {'_color': 'white', '_height': 12}

    # make sure this can be done a second time (since we replaced the __init__ method now)
    w = Wall(color='blue', height=1)
    if native:
        assert vars(w) == {'color': 'blue', 'height': 1}
    else:
        assert vars(w) == {'_color': 'blue', '_height': 1}

    # type hints
    height_field = Wall.__dict__['height']
    color_field = Wall.__dict__['color']

    if py36_style_type_hints:
        assert height_field.type_hint is int
        assert color_field.type_hint is str

        # todo check signature of generated constructor


def test_init_partial_fields():
    class Wall(object):
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        def post_init(self, foo='bar'):
            print(self.height)
            print("post init man !")

        __init__ = make_init(height, post_init_fun=post_init)

    #
    # assert str(signature(Wall.__init__)) == "(self, height, foo='bar')"

    # first init
    w = Wall(12)
    assert vars(w) == {'height': 12}  # color not initialized yet

    # make sure this can be done a second time (since we replaced the __init__ method now)
    w = Wall(foo='blue', height=1)
    assert vars(w) == {'height': 1}  # color not initialized yet


def test_init_order():
    """Tests that order of initialization is the same than order of definition in the class"""

    class C(object):
        y = field()
        x = field(default_factory=copy_field(y))

        @init_fields
        def __init__(self):
            pass

    c = C(y=1)
    print(vars(c))


@pytest.mark.parametrize("a_first", [None, False, True], ids="ancestor_first={}".format)
def test_init_order2(a_first):
    """"""
    class A(object):
        a = field()
        d = field(default=5)

    class B(object):
        b = field()

    class C(B, A):
        a = field(default=None)
        c = field(default_factory=copy_field('b'))

        @init_fields(ancestor_fields_first=a_first)
        def __init__(self):
            pass

    fields = get_fields(C, include_inherited=True, ancestors_first=a_first if a_first is not None else True,
                        _auto_fix_fields=not PY36)
    field_names = [f.name for f in fields]
    if a_first is None or a_first:
        assert field_names == ['a', 'd', 'b', 'c']
    else:
        assert field_names == ['a', 'c', 'b', 'd']

    # make sure that a and c have default values and therefore just passing b is ok.
    c = C(1)
    assert vars(c) == {'b': 1, 'c': 1, 'a': None, 'd': 5}

    c = C(1, 2, 3)
    if a_first is None or a_first:
        assert vars(c) == {'b': 1,  # 1st arg
                           'c': 1,  # default: copy of b
                           'a': 2,  # 2d arg
                           'd': 3   # 3d arg
                           }
    else:
        assert vars(c) == {'b': 1,  # 1st arg
                           'c': 3,  # 3d arg
                           'a': 2,  # 2d arg
                           'd': 5   # default: 5
                           }


def test_init_inheritance():
    """Makes sure that the init method can be generated in inheritance case """

    class A(object):
        a = field(default='hello')

    class B(A):
        b = field(default='world')

        def a(self):
            """ purposedly override the base class field name """
            pass

        __init__ = make_init()

    # make sure that the 'a' field is ok
    b = B(a='h', b='w')
    assert b.a, b.b == ('h', 'w')
