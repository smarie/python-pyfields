import os
import sys
import timeit

import pytest
from valid8 import ValidationError

from pyfields import field, MandatoryFieldInitError, make_init, init_fields


def runs_on_travis():
    return "TRAVIS_PYTHON_VERSION" in os.environ


def test_readme_lazy_fields():

    class Wall(object):
        height = field(doc="Height of the wall in mm.")           # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

    # create an instance
    w = Wall()

    # the field is visible in `dir`
    assert dir(w)[-2:] == ['color', 'height']

    # but not yet in `vars`
    assert vars(w) == dict()

    # lets ask for it - default value is affected
    print(w.color)

    # now it is in `vars` too
    assert vars(w) == {'color': 'white'}

    # mandatory field
    with pytest.raises(MandatoryFieldInitError) as exc_info:
        print(w.height)
    assert str(exc_info.value).startswith("Mandatory field 'height' has not been initialized yet on instance <")

    w.height = 12
    assert vars(w) == {'color': 'white', 'height': 12}


@pytest.mark.parametrize("py36_style_type_hints", [False, True], ids="py36_style_type_hints={}".format)
def test_type_validation(py36_style_type_hints):
    if py36_style_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip()
            Wall = None
        else:
            # import the test that uses python  3.6 type annotations
            from ._test_py36 import _test_readme_type_validation
            Wall = _test_readme_type_validation()
    else:
        class Wall(object):
            height = field(type_hint=int, check_type=True, doc="Height of the wall in mm.")
            color = field(type_hint=str, check_type=True, default='white', doc="Color of the wall.")

    w = Wall()
    w.height = 1
    with pytest.raises(TypeError):
        w.height = "1"


@pytest.mark.parametrize("py36_style_type_hints", [False, True], ids="py36_style_type_hints={}".format)
def test_value_validation(py36_style_type_hints):
    colors = ('blue', 'red', 'white')

    if py36_style_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip()
            Wall = None
        else:
            # import the test that uses python  3.6 type annotations
            from ._test_py36 import _test_readme_value_validation
            Wall = _test_readme_value_validation(colors)

    from mini_lambda import x
    from valid8.validation_lib import is_in

    class Wall(object):
        height = field(type_hint=int,
                       validators={'should be a positive number': x > 0,
                                   'should be a multiple of 100': x % 100 == 0},
                       doc="Height of the wall in mm.")
        color = field(type_hint=str,
                      validators=is_in(colors),
                      default='white', doc="Color of the wall.")

    w = Wall()
    w.height = 100
    with pytest.raises(ValidationError) as exc_info:
        w.height = 1
    assert "Successes: ['x > 0'] / Failures: {" \
           "'x % 100 == 0': 'InvalidValue: should be a multiple of 100. Returned False.'" \
           "}." in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        w.color = 'magenta'
    assert "NotInAllowedValues: x in ('blue', 'red', 'white') does not hold for x=magenta. Wrong value: 'magenta'." \
           in str(exc_info.value)


def test_readme_native_descriptors():
    class Foo:
        a = field()
        b = field(native=False)

    # TODO change when issue with class level access is fixed
    a_name = "test_readme_native_descriptors.<locals>.Foo.a" if sys.version_info >= (3, 6) else "<unknown_cls>.None"
    b_name = "test_readme_native_descriptors.<locals>.Foo.b" if sys.version_info >= (3, 6) else "<unknown_cls>.None"
    assert repr(Foo.__dict__['a']) == "<NativeField: %s>" % a_name
    assert repr(Foo.__dict__['b']) == "<DescriptorField: %s>" % b_name

    f = Foo()

    def set_a(): f.a = 12

    def set_b(): f.b = 12

    def set_c(): f.c = 12

    ta = timeit.Timer(set_a).timeit()
    tb = timeit.Timer(set_b).timeit()
    tc = timeit.Timer(set_c).timeit()

    print("Average time (ns) setting the field:")
    print("%0.2f (normal python) ; %0.2f (native field) ; %0.2f (descriptor field)" % (tc, ta, tb))

    print("Ratio is %.2f" % (ta / tc))

    # make sure that the access time for native field and native are identical
    # for reproducibility on travis, we have to get rid of the first init
    if runs_on_travis():
        print("increasing tolerance on travis.")
        assert ta / tc <= 1.5
    else:
        assert ta / tc <= 1.1
    # assert abs(round(t_field_native * 10) - round(t_native * 10)) <= 1


# def decompose(number):
#     """ decompose a number in scientific notation. from https://stackoverflow.com/a/45359185/7262247"""
#     (sign, digits, exponent) = Decimal(number).as_tuple()
#     fexp = len(digits) + exponent - 1
#     fman = Decimal(number).scaleb(-fexp).normalize()
#     return fman, fexp


def test_readme_make_init_full_defaults():
    class Wall:
        height = field(doc="Height of the wall in mm.")           # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str
        __init__ = make_init()

    # create an instance
    help(Wall)
    with pytest.raises(TypeError) as exc_info:
        Wall()
    assert str(exc_info.value).startswith("__init__()")

    w = Wall(2)
    assert vars(w) == {'color': 'white', 'height': 2}

    w = Wall(color='blue', height=12)
    assert vars(w) == {'color': 'blue', 'height': 12}


def test_readme_make_init_with_explicit_list():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        # only `height` will be in the constructor
        __init__ = make_init(height)

    with pytest.raises(TypeError) as exc_info:
        Wall(1, 'blue')
    assert str(exc_info.value).startswith("__init__()")


def test_readme_make_init_with_inheritance():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        __init__ = make_init(height)

    class ColoredWall(Wall):
        color = field(default='white', doc="Color of the wall.")  # type: str
        __init__ = make_init(Wall.__dict__['height'], color)

    w = ColoredWall(2)
    assert vars(w) == {'color': 'white', 'height': 2}

    w = ColoredWall(color='blue', height=12)
    assert vars(w) == {'color': 'blue', 'height': 12}


def test_readme_make_init_callback():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        def post_init(self, msg='hello'):
            """
            After initialization, some print message is done
            :param msg: the message details to add
            :return:
            """
            print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
            self.non_field_attr = msg

        # only `height` and `foo` will be in the constructor
        __init__ = make_init(height, post_init_fun=post_init)

    w = Wall(1, 'hey')
    assert vars(w) == {'color': 'white', 'height': 1, 'non_field_attr': 'hey'}


def test_readme_init_fields():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        @init_fields
        def __init__(self, msg='hello'):
            """
            After initialization, some print message is done
            :param msg: the message details to add
            :return:
            """
            print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
            self.non_field_attr = msg

    # create an instance
    help(Wall.__init__)
    with pytest.raises(TypeError) as exc_info:
        Wall()
    assert str(exc_info.value).startswith("__init__()")

    w = Wall(2)
    assert vars(w) == {'color': 'white', 'height': 2, 'non_field_attr': 'hello'}

    w = Wall(msg='hey', color='blue', height=12)
    assert vars(w) == {'color': 'blue', 'height': 12, 'non_field_attr': 'hey'}
