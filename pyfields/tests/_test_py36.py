#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

import pytest

from typing import List
from pyfields import field, inject_fields, MandatoryFieldInitError, make_init, autofields


def _test_class_annotations():
    class Foo:
        field_with_validate_type: int = field(check_type=True)
        field_with_defaults: str = field()

    return Foo


def _test_readme_type_validation():
    class Wall(object):
        height: int = field(check_type=True, doc="Height of the wall in mm.")
        color: str = field(check_type=True, default='white', doc="Color of the wall.")

    return Wall


def _test_readme_value_validation(colors):
    from mini_lambda import x
    from valid8.validation_lib import is_in

    class Wall(object):
        height: int = field(validators={'should be a positive number': x > 0,
                                        'should be a multiple of 100': x % 100 == 0},
                            doc="Height of the wall in mm.")
        color: str = field(validators=is_in(colors),
                           default='white',
                           doc="Color of the wall.")

    return Wall


def test_value_validation_advanced(validate_width):
    class Wall(object):
        height: int = field(doc="Height of the wall in mm.")
        width: str = field(validators=validate_width,
                           doc="Width of the wall in mm.")
    return Wall


def _test_readme_constructor(explicit_fields_list, init_type, native):
    if init_type == 'inject_fields':
        if explicit_fields_list:
            class Wall:
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)

                @inject_fields(height, color)
                def __init__(self, fields):
                    with pytest.raises(MandatoryFieldInitError):
                        print(self.height)

                    # initialize all fields received
                    fields.init(self)
        else:
            class Wall:
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)

                @inject_fields
                def __init__(self, fields):
                    with pytest.raises(MandatoryFieldInitError):
                        print(self.height)

                    # initialize all fields received
                    fields.init(self)
    elif init_type == 'make_init':
        if explicit_fields_list:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)
                __init__ = make_init(height, color)
        else:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)
                __init__ = make_init()
    elif init_type == 'make_init_with_postinit':
        if explicit_fields_list:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)

                def post_init(self, foo: str = 'bar'):
                    print(self.height)
                    print("post init man !")
                __init__ = make_init(height, color, post_init_fun=post_init)
        else:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.", native=native)
                color: str = field(default='white', doc="Color of the wall.", native=native)

                def post_init(self, foo: str = 'bar'):
                    print(self.height)
                    print("post init man !")

                __init__ = make_init(post_init_fun=post_init)
    else:
        raise ValueError(init_type)

    return Wall


def _test_autofields(type_check):
    if type_check:
        _deco = autofields(check_types=True)
    else:
        _deco = autofields

    @_deco
    class Foo:
        CONSTANT: str = 's'
        __a__: int = 0

        foo: int
        bar = 0
        barcls = int
        barfunc = lambda x: x
        barbar: str

        class cls:
            pass

        def fct(self):
            return 1

    return Foo


def _test_autofields_readme():

    @autofields(autoinit=True)
    class Item:
        name: str

    @autofields
    class Pocket:
        size: int
        items: List[Item] = []

    @autofields
    class Pocket2:
        size: int
        items: List[Item] = []
        def __init__(self, who):
            print("hello, %s" % who)

    return Pocket, Item, Pocket2
