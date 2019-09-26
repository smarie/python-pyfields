#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import pytest

from pyfields import field, inject_fields, MandatoryFieldInitError


def _test_class_annotations():
    class Foo:
        field_with_native_forced_to_false: int = field(native=False)
        field_with_defaults: str = field()

    return Foo


def _test_readme_constructor_1():

    class Wall:
        height: int = field(doc="Height of the wall in mm.")
        color: str = field(default='white', doc="Color of the wall.")

        @inject_fields(height, color)
        def __init__(self, fields):
            with pytest.raises(MandatoryFieldInitError):
                self.height

            # initialize all fields received
            fields.init(self)

    return Wall
