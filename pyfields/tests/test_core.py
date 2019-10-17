#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import sys
from collections import OrderedDict

import pytest

from valid8 import ValidationError, ValidationFailure
from valid8.base import InvalidValue
from valid8.validation_lib import non_empty, Empty

from pyfields import field, MandatoryFieldInitError, UnsupportedOnNativeFieldError, inject_fields, make_init, \
    copy_value, copy_field, Converter, Field, ConversionError, ReadOnlyFieldError


@pytest.mark.parametrize('write_before_reading', [False, True], ids="write_before_reading={}".format)
@pytest.mark.parametrize('type_', ['default_factory', 'default', 'mandatory'], ids="type_={}".format)
@pytest.mark.parametrize('read_only', [False, True], ids="read_only={}".format)
def test_field(write_before_reading, type_, read_only):
    """Checks that field works as expected"""

    if type_ == 'default_factory':
        class Tweety(object):
            afraid = field(default_factory=lambda obj: False, read_only=read_only)
    elif type_ == 'default':
        class Tweety(object):
            afraid = field(default=False, read_only=read_only)
    elif type_ == 'mandatory':
        class Tweety(object):
            afraid = field(read_only=read_only)
    else:
        raise ValueError()

    # instantiate
    t = Tweety()

    written = False

    # (1) write
    if write_before_reading:
        t.afraid = True
        written = True

    # (2) read
    if not write_before_reading and type_ == 'mandatory':
        # mandatory value not already overridden
        with pytest.raises(MandatoryFieldInitError):
            print(t.afraid)
    else:
        # either default value (False) or already-written value (True)
        assert t.afraid is write_before_reading
        written = True  # because reading a non-mandatory field sets it to default

    # (3) write (possibly again) and check
    if not (read_only and written):
        t.afraid = True
        assert t.afraid is True
        if not read_only:
            t.afraid = False
            assert t.afraid is False
        written = True

    # if read only, check exception on second write
    if read_only:
        # make sure that now the value has been
        assert written

        with pytest.raises(ReadOnlyFieldError) as exc_info:
            t.afraid = False
        qualname = Tweety.__dict__['afraid'].qualname
        assert str(exc_info.value) == "Read-only field '%s' has already been " \
                                      "initialized on instance %s and cannot be modified anymore." % (qualname, t)


def test_slots():
    """tests that fields are replaced with descriptor fields automatically when used on a class with `__slots__`"""
    class WithSlots(object):
        __slots__ = ('_a',)
        a = field()

    if sys.version_info < (3, 0):
        # qualname does not exist, we use str(cls)
        a_fixed_name = "pyfields.tests.test_core.WithSlots.a"
    else:
        a_fixed_name = "test_slots.<locals>.WithSlots.a"

    a_unknown_name = "<unknown_cls>.None"

    if sys.version_info >= (3, 6):
        # change is done immediately
        assert repr(WithSlots.__dict__['a']) == "<DescriptorField: %s>" % a_fixed_name
    else:
        # change will be done after first access
        assert repr(WithSlots.__dict__['a']) == "<NativeField: %s>" % a_unknown_name

    w = WithSlots()

    if sys.version_info < (3, 6):
        # Really not ideal you have to do something
        try:
            w.a
        except:
            pass

    w.a = 1
    assert w.a == 1

    assert repr(WithSlots.__dict__['a']) == "<DescriptorField: %s>" % a_fixed_name


def test_slots2():
    class WithSlots(object):
        __slots__ = ('__dict__',)
        a = field()

    if sys.version_info >= (3, 6):
        a_name = "test_slots2.<locals>.WithSlots.a"
    else:
        a_name = "<unknown_cls>.None"
    assert repr(WithSlots.__dict__['a']) == "<NativeField: %s>" % a_name


def test_default_factory():
    """"""
    class Foo(object):
        a = field(default_factory=copy_value([]))
        b = field(default_factory=copy_field('z'))
        c = field()

        @c.default_factory
        def c_default(self):
            return self.a + ['yes']

        z = field()

    f = Foo()
    g = Foo()
    assert f.a == []
    assert g.a == []
    g.a.append(1)
    assert g.a == [1]
    assert f.a == []
    # we can not initialize b since it requires a copy of uninitialized z
    with pytest.raises(MandatoryFieldInitError) as exc_info:
        print(f.b)
    assert str(exc_info.value).startswith("Mandatory field 'z' has not been initialized yet")
    # if we initialize z we can now safely make a copy
    f.z = 12
    assert f.b == 12
    f.z += 1
    assert f.z == 13
    assert f.b == 12

    assert g.c == [1, 'yes']


def test_type():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    class Foo(object):
        f = field(type_hint=str, check_type=True)

    o = Foo()
    o.f = 'hello'
    with pytest.raises(TypeError) as exc_info:
        o.f = 1

    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type %s. " \
                                  "Instead, received a 'int': 1" % (qualname, str)


def test_type_multiple_tuple():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    class Foo(object):
        f = field(type_hint=(str, int), check_type=True)

    o = Foo()
    o.f = 'hello'
    o.f = 1
    with pytest.raises(TypeError) as exc_info:
        o.f = 1.1

    # msg = Value type should be one of ('str', 'int')
    msg = "Value should be of type (%s, %s)" % (str, int)
    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type_multiple_tuple.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "%s. " \
                                  "Instead, received a 'float': 1.1" % (qualname, msg)


def test_type_multiple_typing():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    from typing import Union

    class Foo(object):
        f = field(type_hint=Union[int, str], check_type=True)

    o = Foo()
    o.f = 'hello'
    o.f = 1
    with pytest.raises(TypeError) as exc_info:
        o.f = 1.1

    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type_multiple_typing.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type typing.Union[int, str]. " \
                                  "Instead, received a 'float': 1.1" % qualname


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not allowed before python 3.6")
def test_type_from_pep484_annotations():
    # import the class to use
    from ._test_py36 import _test_class_annotations
    Foo = _test_class_annotations()

    # create an instance
    foo = Foo()

    # test that the field that is non-native has type checking active
    foo.field_with_validate_type = 2
    with pytest.raises(TypeError) as exc_info:
        foo.field_with_validate_type = 'hello'
    assert str(exc_info.value).startswith("Invalid value type provided for ")

    # by default the type is not checked
    foo.field_with_defaults = 'hello'


@pytest.mark.parametrize("case_nb", [1, 2, 3, 4, 5], ids="case_nb={}".format)
def test_field_validators(case_nb):
    """ tests that `validators` functionality works correctly with several flavours of definition."""

    # class EmptyError(ValidationError):
    #     help_msg = "h should be non empty"

    class EmptyFailure(ValidationFailure, ValueError):
        """ Custom ValidationFailure raised by non_empty """
        help_msg = 'len(x) > 0 does not hold for x={wrong_value}'

    class Foo2(object):
        # one single validator
        f = field(default="hey", type_hint=str, validators=non_empty)

        # one single validator in a list
        g = field(type_hint=str, validators=[non_empty])

        # one single validator accepting three arguments (obj, field, val)
        gg = field(type_hint=str, validators=lambda obj, field, val: obj.f in val)

        # several validators in a dict. keys and values can contain elements of definition in any order
        h = field(type_hint=str, validators=OrderedDict([("h should be non empty", (non_empty, EmptyFailure)),
                                                         ("h should contain field f", (lambda obj, val: obj.f in val)),
                                                         ("h should contain 'a'", (lambda val: 'a' in val))]))

    if sys.version_info < (3, 0):
        # qualname does not exist, we use str(cls)
        c_name = "pyfields.tests.test_core.Foo2"
    else:
        c_name = "test_field_validators.<locals>.Foo2"

    # the object that we'll use
    o = Foo2()

    if case_nb == 1:
        o.f = 'hey'
        with pytest.raises(ValidationError) as exc_info:
            o.f = ''
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, Empty)
        assert str(exc_info.value) == "Error validating [%s.f='']. " \
                                      "Empty: len(x) > 0 does not hold for x=. Wrong value: ''." % c_name

    elif case_nb == 2:
        o.g = 'hey'
        with pytest.raises(ValidationError) as exc_info:
            o.g = ''
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, Empty)
        assert str(exc_info.value) == "Error validating [%s.g='']. " \
                                      "Empty: len(x) > 0 does not hold for x=. Wrong value: ''." % c_name

    elif case_nb == 3:
        o.gg = 'heyho'
        with pytest.raises(ValidationError) as exc_info:
            o.gg = 'ho'  # does not contain field f ('hey')
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, InvalidValue)
        assert exc_info.value.failure.validation_outcome is False
        assert str(exc_info.value) == "Error validating [%s.gg=ho]. " \
                                      "InvalidValue: Function [<lambda>] returned [False] for value 'ho'." % c_name

    elif case_nb in (4, 5):
        if case_nb == 4:
            # override the definition for Foo2.h
            # several validators in a list. Tuples should start with the function
            Foo2.h = field(name='h', type_hint=str, validators=[(non_empty, "h should be non empty", EmptyFailure),
                                                                non_empty,
                                                                (lambda obj, val: obj.f in val, "h should contain field f"),
                                                                (lambda val: 'a' in val, "h should contain 'a'"),
                                                                (non_empty, EmptyFailure),
                                                                ])

        # o.h should be a non-empty string containing 'a' and containing o.f
        with pytest.raises(ValidationError) as exc_info:
            o.h = ''  # empty
        str(exc_info.value)
        assert isinstance(exc_info.value.failure.__cause__, EmptyFailure)
        assert str(exc_info.value.failure.__cause__) == "h should be non empty. " \
                                                        "Function [non_empty] raised " \
                                                        "Empty: len(x) > 0 does not hold for x=. Wrong value: ''."

        with pytest.raises(ValidationError) as exc_info:
            o.h = 'hey'  # does not contain 'a'
        assert isinstance(exc_info.value.failure.__cause__, InvalidValue)
        assert exc_info.value.failure.__cause__.validation_outcome is False
        assert str(exc_info.value.failure.__cause__) == "h should contain 'a'. " \
                                                        "Function [<lambda>] returned [False] for value 'hey'."

        with pytest.raises(ValidationError) as exc_info:
            o.h = 'a'  # does not contain field f ('hey')
        assert isinstance(exc_info.value.failure.__cause__, InvalidValue)
        assert exc_info.value.failure.__cause__.validation_outcome is False
        assert str(exc_info.value.failure.__cause__) == "h should contain field f. " \
                                                        "Function [<lambda>] returned [False] for value 'a'."
        o.h = 'hey ya'


@pytest.mark.parametrize("explicit", [False, True], ids="explicit={}".format)
def test_field_validators_decorator(explicit):
    """Tests that the @<field>.decorator works correctly"""

    if explicit:
        native = False
    else:
        native = None
        if sys.version_info < (3, 6):
            with pytest.raises(UnsupportedOnNativeFieldError):
                class Foo(object):
                    f = field(native=native)
                    @f.validator
                    def validate_f(self, val):
                        return val % 3 == 0
            return

    class Foo(object):
        f = field(native=native)

        @f.validator
        def f_should_be_a_multiple_of_3(self, f_val):
            return f_val % 3 == 0

        @f.validator(help_msg="not a large enough value")
        def f_should_be_larger_than_g(self, f_val):
            return f_val > self.g

    f_field = Foo.__dict__['f']
    assert len(f_field.root_validator.base_validation_funcs) == 2
    foo = Foo()
    foo.g = 0
    with pytest.raises(ValidationError) as exc_info:
        foo.f = 2
    # assert str(exc_info.value) == "Error validating [%s=2]. " \
    #                               "InvalidValue: Function [f_should_be_a_multiple_of_3] returned [False] for value 2." \
    #        % Foo.__dict__['f'].qualname
    assert str(exc_info.value) == "Error validating [%s=2]. At least one validation function failed for value 2. " \
                                  "Successes: ['f_should_be_larger_than_g'] / " \
                                  "Failures: {'f_should_be_a_multiple_of_3': 'Returned False.'}." \
           % Foo.__dict__['f'].qualname
    foo.f = 3
    foo.g = 3
    with pytest.raises(ValidationError) as exc_info:
        foo.f = 3
    assert str(exc_info.value) == "Error validating [%s=3]. At least one validation function failed for value 3. " \
                                  "Successes: ['f_should_be_a_multiple_of_3'] / " \
                                  "Failures: {'f_should_be_larger_than_g': " \
                                  "'InvalidValue: not a large enough value. Returned False.'}." \
           % Foo.__dict__['f'].qualname


def test_validator_not_compliant_with_native_field():
    """tests that `native=True` can not be set when a validator is provided"""
    with pytest.raises(UnsupportedOnNativeFieldError):
        class Foo(object):
            f = field(validators=lambda x: True, native=True)


@pytest.mark.parametrize("explicit", [False, True], ids="explicit={}".format)
def test_field_converters_decorator(explicit):
    """Tests that the @<field>.converter works correctly"""

    if explicit:
        native = False
    else:
        native = None
        if sys.version_info < (3, 6):
            with pytest.raises(UnsupportedOnNativeFieldError):
                class Foo(object):
                    f = field(native=native)
                    @f.converter
                    def validate_f(self, val):
                        return val % 3 == 0
            return

    class Foo(object):
        f = field(native=native)

        @f.converter(accepts=str)
        def f_from_str(self, f_val):
            # make sure the filter has worked
            assert isinstance(f_val, str)
            return int(f_val)

        @f.converter
        def f_from_anything(self, f_val):
            if isinstance(f_val, int):
                # of course we would not do that in real life but this is a test that exceptions are supported
                raise Exception("no need to convert! already an int")
            return int(f_val) + 1

    f_field = Foo.__dict__['f']
    assert len(f_field.converters) == 2
    foo = Foo()
    foo.f = 0    # uses no converter at all
    assert foo.f == 0
    foo.f = '2'  # uses the first converter
    assert foo.f == 2
    foo.f = 2.1  # uses the second converter
    assert foo.f == 3


def test_converter_not_compliant_with_native_field():
    """tests that `native=True` can not be set when a validator is provided"""
    with pytest.raises(UnsupportedOnNativeFieldError):
        class Foo(object):
            f = field(converters=lambda x: x, native=True)


@pytest.mark.parametrize("validator_return_none", [False, True], ids="validator_return_none={}".format)
@pytest.mark.parametrize("nbargs", [1, 2, 3], ids="nbargs={}".format)
@pytest.mark.parametrize("format", ['single_converter', 'single_fun',
                                    '(v_fun, c_fun)', '(v_type, c_fun)', '(joker, c_fun)', '(None, c_fun)',
                                    '{v_fun: c_fun}', '{v_type: c_fun}', '{joker: c_fun}', '{None: c_fun}'],
                         ids="format={}".format)
def test_converters(format, nbargs, validator_return_none):
    """Various tests about converters definition format"""

    from mini_lambda import x

    if nbargs == 1:
        def parse_nb(x):
            return int(x)

        def valid_str(x):
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    elif nbargs == 2:
        def parse_nb(obj, x):
            assert obj.__class__.__name__ == 'Foo'
            return int(x)

        def valid_str(obj, x):
            assert obj.__class__.__name__ == 'Foo'
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    elif nbargs == 3:
        def parse_nb(obj, field, x):
            assert obj.__class__.__name__ == 'Foo'
            assert isinstance(field, Field)
            return int(x)

        def valid_str(obj, field, x):
            assert obj.__class__.__name__ == 'Foo'
            assert isinstance(field, Field)
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    else:
        raise ValueError(nbargs)

    if format == 'single_converter':
        class ParseNb(Converter):
            def convert(self, obj, field, x):
                if nbargs == 1:
                    return parse_nb(x)
                elif nbargs == 2:
                    return parse_nb(obj, x)
                elif nbargs == 3:
                    return parse_nb(obj, field, x)
        convs = ParseNb()
        accepts_int = True
        c_name = "ParseNb"

    elif format == 'single_fun':
        convs = parse_nb
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '(v_fun, c_fun)':
        convs = (valid_str, parse_nb)
        accepts_int = False
        c_error_details = "Acceptance test: REJECTED (returned False)"
        c_name = 'parse_nb'

    elif format == '(v_type, c_fun)':
        convs = (str, parse_nb)
        accepts_int = False
        c_error_details = "Acceptance test: ERROR [HasWrongType] Value should be an instance of %s. " \
                          "Wrong value: 1." % str
        c_name = 'parse_nb'

    elif format == '(joker, c_fun)':
        convs = ('*', parse_nb)
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '(None, c_fun)':
        convs = (None, parse_nb)
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '{v_fun: c_fun}':
        convs = {valid_str: parse_nb}
        accepts_int = False
        c_error_details = "Acceptance test: REJECTED (returned False)"
        c_name = 'parse_nb'

    elif format == '{v_type: c_fun}':
        convs = {str: parse_nb}
        accepts_int = False
        c_error_details = "Acceptance test: ERROR [HasWrongType] Value should be an instance of %s. " \
                          "Wrong value: 1." % str
        c_name = 'parse_nb'

    elif format == '{joker: c_fun}':
        convs = {'*': parse_nb}
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '{None: c_fun}':
        convs = {None: parse_nb}
        accepts_int = True
        c_name = 'parse_nb'

    else:
        raise ValueError(format)

    class Foo(object):
        f = field(converters=convs, validators=[x % 3 == 0])

    o = Foo()
    f_field = Foo.__dict__['f']
    f_converters = f_field.converters
    assert len(f_converters) == 1 and isinstance(f_converters[0], Converter)
    o.f = 3
    o.f = '6'
    assert o.f == 6
    with pytest.raises(ValueError) as exc_info:
        o.f = '5'
    if sys.version_info < (3, 0):
        qualname = "pyfields.tests.test_core.Foo.f"  # qualname does not exist, we use str(cls)
    else:
        qualname = "test_converters.<locals>.Foo.f"
    assert str(exc_info.value) == "Error validating [%s=5]. " \
                                  "InvalidValue: Function [x %% 3 == 0] returned [False] for value 5." % qualname

    if accepts_int:
        if nbargs == 1:
            converted_value, details = f_field.trace_convert(1)
        else:
            # we have to provide the object, as it is used in our converter
            converted_value, details = f_field.trace_convert(1, obj=o)

        assert converted_value == 1
        assert str(details) == """Value 1 successfully converted to 1 using converter '%s', after the following attempts:
 - Converter '%s': Acceptance test: SUCCESS (returned None). Conversion: SUCCESS -> 1
""" % (c_name, c_name)
    else:
        with pytest.raises(ConversionError) as exc_info:
            if nbargs == 1:
                converted_value, details = f_field.trace_convert(1)
            else:
                # we have to provide the object, as it is used in our converter
                converted_value, details = f_field.trace_convert(1, obj=o)
        assert str(exc_info.value) == """Unable to convert value 1. Results:
 - Converter '%s': %s
""" % (c_name, c_error_details)


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
