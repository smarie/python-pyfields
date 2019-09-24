#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import pytest

from pyfields import field


def _test_class_annotations():
    class Foo:
        field_with_native_forced_to_false: int = field(native=False)
        field_with_defaults: str = field()

    return Foo
