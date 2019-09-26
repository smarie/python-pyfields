#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import pytest

from pyfields import field, inject_fields, MandatoryFieldInitError, make_init


def _test_class_annotations():
    class Foo:
        field_with_native_forced_to_false: int = field(native=False)
        field_with_defaults: str = field()

    return Foo


def _test_readme_constructor(explicit_fields_list, init_type):
    if init_type == 'inject_fields':
        if explicit_fields_list:
            class Wall:
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")

                @inject_fields(height, color)
                def __init__(self, fields):
                    with pytest.raises(MandatoryFieldInitError):
                        self.height

                    # initialize all fields received
                    fields.init(self)
        else:
            class Wall:
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")

                @inject_fields
                def __init__(self, fields):
                    with pytest.raises(MandatoryFieldInitError):
                        self.height

                    # initialize all fields received
                    fields.init(self)
    elif init_type == 'make_init':
        if explicit_fields_list:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")
                __init__ = make_init(height, color)
        else:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")
                __init__ = make_init()
    elif init_type == 'make_init_with_postinit':
        if explicit_fields_list:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")

                def post_init(self, foo: str = 'bar'):
                    self.height
                    print("post init man !")
                __init__ = make_init(height, post_init, color)
        else:
            class Wall(object):
                height: int = field(doc="Height of the wall in mm.")
                color: str = field(default='white', doc="Color of the wall.")

                def post_init(self, foo: str = 'bar'):
                    self.height
                    print("post init man !")

                __init__ = make_init(post_init)
    else:
        raise ValueError(init_type)

    return Wall
