#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import pytest

from pyfields import field, inject_fields, MandatoryFieldInitError, make_init


def _test_class_annotations():
    class Foo:
        field_with_validate_type: int = field(check_type=True)
        field_with_defaults: str = field()

    return Foo


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
