import os
import sys
import timeit

import pytest
from valid8 import ValidationError, ValidationFailure

from pyfields import field, MandatoryFieldInitError, make_init, init_fields, ReadOnlyFieldError, NoneError, \
    FieldTypeError


def runs_on_travis():
    return "TRAVIS_PYTHON_VERSION" in os.environ


def test_lazy_fields():

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


@pytest.mark.parametrize("use_decorator", [False, True], ids="use_decorator={}".format)
def test_default_factory(use_decorator):

    class BadPocket(object):
        items = field(default=[])

    p = BadPocket()
    p.items.append('thing')
    g = BadPocket()
    assert g.items == ['thing']

    if use_decorator:
        class Pocket:
            items = field()

            @items.default_factory
            def default_items(self):
                return []
    else:
        class Pocket(object):
            items = field(default_factory=lambda obj: [])

    p = Pocket()
    g = Pocket()
    p.items.append('thing')
    assert p.items == ['thing']
    assert g.items == []


def test_readonly_field():
    """ checks that the example in the readme is correct """

    class User(object):
        name = field(read_only=True)

    u = User()
    u.name = "john"
    assert "name: %s" % u.name == "name: john"
    with pytest.raises(ReadOnlyFieldError) as exc_info:
        u.name = "john2"
    qualname = User.name.qualname
    assert str(exc_info.value) == "Read-only field '%s' has already been " \
                                  "initialized on instance %s and cannot be modified anymore." % (qualname, u)

    class User(object):
        name = field(read_only=True, default="dummy")

    u = User()
    assert "name: %s" % u.name == "name: dummy"
    with pytest.raises(ReadOnlyFieldError):
        u.name = "john"


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


@pytest.mark.parametrize("py36_style_type_hints", [False, True], ids="py36_style_type_hints={}".format)
def test_value_validation_advanced(py36_style_type_hints):

    class InvalidWidth(ValidationFailure):
        help_msg = 'should be a multiple of the height ({height})'

    def validate_width(obj, width):
        if width % obj.height != 0:
            raise InvalidWidth(width, height=obj.height)

    if py36_style_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip()
            Wall = None
        else:
            # import the test that uses python  3.6 type annotations
            from ._test_py36 import test_value_validation_advanced
            Wall = test_value_validation_advanced(validate_width)
    else:
        class Wall(object):
            height = field(type_hint=int,
                           doc="Height of the wall in mm.")
            width = field(type_hint=str,
                          validators=validate_width,
                          doc="Width of the wall in mm.")

    w = Wall()
    w.height = 100
    w.width = 200

    with pytest.raises(ValidationError) as exc_info:
        w.width = 201
    assert "InvalidWidth: should be a multiple of the height (100). Wrong value: 201." in str(exc_info.value)

try:
    from typing import Optional
    typing_present = True
except ImportError:
    typing_present = False


@pytest.mark.skipif(not typing_present, reason="typing module is not present")
@pytest.mark.parametrize("declaration", ['typing', 'default_value', 'explicit_nonable'], ids="declaration={}".format)
def test_nonable_fields(declaration):
    """Tests that nonable fields are supported and correctly handled"""

    if declaration == 'typing':
        from typing import Optional
        
        class Foo(object):
            a = field(type_hint=Optional[int], check_type=True)
            b = field(type_hint=Optional[int], validators={'is positive': lambda x: x > 0})
            c = field(nonable=False, check_type=True)
            d = field(validators={'accept_all': lambda x: True})
            e = field(nonable=False)

    elif declaration == 'default_value':
        class Foo(object):
            a = field(type_hint=int, default=None, check_type=True)
            b = field(type_hint=int, default=None, validators={'is positive': lambda x: x > 0})
            c = field(nonable=False, check_type=True)
            d = field(validators={'accept_all': lambda x: True})
            e = field(nonable=False)

    elif declaration == 'explicit_nonable':
        class Foo(object):
            a = field(type_hint=int, nonable=True, check_type=True)
            b = field(type_hint=int, nonable=True, validators={'is positive': lambda x: x > 0})
            c = field(nonable=False, check_type=True)
            d = field(validators={'accept_all': lambda x: True})
            e = field(nonable=False)

    else:
        raise ValueError(declaration)

    f = Foo()
    f.a = None
    f.b = None
    with pytest.raises(NoneError):
        f.c = None
    f.d = None
    f.e = None
    assert vars(f) == {'_a': None, '_b': None, '_d': None, 'e': None}


def test_native_descriptors():
    """"""
    class Foo:
        a = field()
        b = field(native=False)

    # TODO change when issue with class level access is fixed
    a_name = "test_native_descriptors.<locals>.Foo.a" if sys.version_info >= (3, 6) else "<unknown_cls>.None"
    b_name = "test_native_descriptors.<locals>.Foo.b" if sys.version_info >= (3, 6) else "<unknown_cls>.None"
    assert repr(Foo.a) == "<NativeField: %s>" % a_name
    assert repr(Foo.b) == "<DescriptorField: %s>" % b_name

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
        assert ta / tc <= 2.0
    else:
        assert ta / tc <= 1.1
    # assert abs(round(t_field_native * 10) - round(t_native * 10)) <= 1


# def decompose(number):
#     """ decompose a number in scientific notation. from https://stackoverflow.com/a/45359185/7262247"""
#     (sign, digits, exponent) = Decimal(number).as_tuple()
#     fexp = len(digits) + exponent - 1
#     fman = Decimal(number).scaleb(-fexp).normalize()
#     return fman, fexp


def test_make_init_full_defaults():
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


def test_make_init_with_explicit_list():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        # only `height` will be in the constructor
        __init__ = make_init(height)

    with pytest.raises(TypeError) as exc_info:
        Wall(1, 'blue')
    assert str(exc_info.value).startswith("__init__()")


def test_make_init_with_inheritance():
    class Wall:
        height = field(doc="Height of the wall in mm.")  # type: int
        __init__ = make_init(height)

    class ColoredWall(Wall):
        color = field(default='white', doc="Color of the wall.")  # type: str
        __init__ = make_init(Wall.height, color)

    w = ColoredWall(2)
    assert vars(w) == {'color': 'white', 'height': 2}

    w = ColoredWall(color='blue', height=12)
    assert vars(w) == {'color': 'blue', 'height': 12}


def test_make_init_callback():
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


def test_init_fields():
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


no_type_checker = False
try:
    import typeguard
except ImportError:
    try:
        import pytypes
    except ImportError:
        no_type_checker = True


@pytest.mark.skipif(sys.version_info < (3, 6), reason="python < 3.6 does not support class member type hints")
@pytest.mark.skipif(no_type_checker, reason="no type checker is installed")
def test_autofields_readme():
    """Test for readme on autofields"""

    from ._test_py36 import _test_autofields_readme
    Pocket, Item, Pocket2 = _test_autofields_readme()

    with pytest.raises(TypeError):
        Item()

    item1 = Item(name='1')
    pocket1 = Pocket(size=2)
    pocket2 = Pocket(size=2)

    # make sure that custom constructor is not overridden by @autofields
    pocket3 = Pocket2("world")
    with pytest.raises(MandatoryFieldInitError):
        pocket3.size

    # make sure the items list is not the same in both (if we add the item to one, they do not appear in the 2d)
    assert pocket1.size == 2
    assert pocket1.items is not pocket2.items
    pocket1.items.append(item1)
    assert len(pocket2.items) == 0


try:
    import pytypes
except ImportError:
    has_pytypes = False
else:
    has_pytypes = True


@pytest.mark.skipif(has_pytypes, reason="pytypes does not correctly support vtypes - "
                                        "see https://github.com/Stewori/pytypes/issues/86")
@pytest.mark.skipif(sys.version_info < (3, 6), reason="python < 3.6 does not support class member type hints")
def test_autofields_vtypes_readme():

    from ._test_py36 import _test_autofields_vtypes_readme
    Rectangle = _test_autofields_vtypes_readme()

    r = Rectangle(1, 2)
    with pytest.raises(FieldTypeError):
        Rectangle(1, -2)
    with pytest.raises(FieldTypeError):
        Rectangle('1', 2)


def test_autoclass():
    """ Tests the example with autoclass in the doc """
    from autoclass import autoclass

    @autoclass
    class Foo(object):
        msg = field(type_hint=str)
        age = field(default=12, type_hint=int)

    foo = Foo(msg='hello')

    print(foo)  # automatic string representation
    print(dict(foo))  # dict view

    assert str(foo) == "Foo(msg='hello', age=12)"
    assert str(dict(foo)) in ("{'msg': 'hello', 'age': 12}", "{'age': 12, 'msg': 'hello'}")
    assert foo == Foo(msg='hello', age=12)  # comparison (equality)
    assert foo == {'msg': 'hello', 'age': 12}  # comparison with dicts
