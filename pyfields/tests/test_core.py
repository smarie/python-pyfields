#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import sys
from collections import OrderedDict

import pytest

from valid8 import ValidationError,ValidationFailure
from valid8.base import InvalidValue
from valid8.validation_lib import non_empty, Empty

from pyfields import field, MandatoryFieldInitError, UnsupportedOnNativeFieldError, with_fields, make_init


@pytest.mark.parametrize('read_first', [False, True], ids="read_first={}".format)
@pytest.mark.parametrize('type_', ['default_factory', 'default', 'mandatory'], ids="type_={}".format)
def test_field(read_first, type_):
    """Checks that field works as expected"""

    if type_ == 'default_factory':
        class Tweety:
            afraid = field(default_factory=lambda: False)
    elif type_ == 'default':
        class Tweety:
            afraid = field(default=False)
    elif type_ == 'mandatory':
        class Tweety:
            afraid = field()
    else:
        raise ValueError()

    # instantiate
    t = Tweety()

    if not read_first:
        # set
        t.afraid = False

    # read
    if read_first and type_ == 'mandatory':
        with pytest.raises(MandatoryFieldInitError):
            assert not t.afraid
    else:
        assert not t.afraid

    # set
    t.afraid = True
    assert t.afraid


def test_type():
    """ Tests that when `type` is provided, it works as expected """

    class Foo(object):
        f = field(type=str)

    o = Foo()
    o.f = 'hello'
    with pytest.raises(TypeError) as exc_info:
        o.f = 1

    assert str(exc_info.value) == "Invalid value type provided for 'Foo.f'. " \
                                  "Value should be of type 'str'. " \
                                  "Instead, received a 'int': 1"


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not allowed before python 3.6")
def test_type_from_pep484_annotations():
    # import the class to use
    from ._test_py36 import _test_class_annotations
    Foo = _test_class_annotations()

    # create an instance
    foo = Foo()

    # test that the field that is non-native has type checking active
    foo.field_with_native_forced_to_false = 2
    with pytest.raises(TypeError) as exc_info:
        foo.field_with_native_forced_to_false = 'hello'
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
        f = field(default="hey", type=str, validators=non_empty)

        # one single validator in a list
        g = field(type=str, validators=[non_empty])

        # one single validator accepting three arguments (obj, field, val)
        gg = field(type=str, validators=lambda obj, field, val: obj.f in val)

        # several validators in a dict. keys and values can contain elements of definition in any order
        h = field(type=str, validators=OrderedDict([("h should be non empty", (non_empty, EmptyFailure)),
                                                    ("h should contain field f", (lambda obj, val: obj.f in val)),
                                                    ("h should contain 'a'", (lambda val: 'a' in val))]))

    if sys.version_info < (3, 6):
        c_name = "<unknown_cls>"
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
            Foo2.h = field(name='h', type=str, validators=[(non_empty, "h should be non empty", EmptyFailure),
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


def test_validator_not_compliant_with_native_field():
    """tests that `native=True` can not be set when a validator is provided"""
    with pytest.raises(UnsupportedOnNativeFieldError):
        class Foo(object):
            f = field(validators=lambda x: True, native=True)


@pytest.mark.parametrize("init_type", ['with_fields', 'make_init', 'make_init_with_postinit'], ids="init_type={}".format)
@pytest.mark.parametrize("explicit_fields_list", [False, True], ids="explicit_list={}".format)
@pytest.mark.parametrize("py36_style_type_hints", [False, True], ids="py36_style_type_hints={}".format)
def test_init_all_methods(py36_style_type_hints, explicit_fields_list, init_type):
    """Test of @with_fields with selected fields """
    if py36_style_type_hints:
        if sys.version_info < (3, 6):
            pytest.skip()
            Wall = None
        else:
            # import the test that uses python  3.6 type annotations
            from ._test_py36 import _test_readme_constructor
            Wall = _test_readme_constructor(explicit_fields_list, init_type)
    else:
        if init_type == 'with_fields':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")          # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str

                    @with_fields(height, color)
                    def __init__(self, fields):
                        with pytest.raises(MandatoryFieldInitError):
                            self.height
                        # initialize all fields received
                        fields.init(self)
                        self.height
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")  # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str

                    @with_fields
                    def __init__(self, fields):
                        with pytest.raises(MandatoryFieldInitError):
                            self.height
                        # initialize all fields received
                        fields.init(self)
                        self.height

        elif init_type == 'make_init':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")  # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str
                    __init__ = make_init(height, color)
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")  # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str
                    __init__ = make_init()

        elif init_type == 'make_init_with_postinit':
            if explicit_fields_list:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")  # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str
                    def post_init(self, foo='bar'):
                        self.height
                        print("post init man !")

                    __init__ = make_init(height, post_init, color)
            else:
                class Wall(object):
                    height = field(doc="Height of the wall in mm.")  # type: int
                    color = field(default='white', doc="Color of the wall.")  # type: str
                    def post_init(self, foo='bar'):
                        self.height
                        print("post init man !")

                    __init__ = make_init(post_init)
        else:
            raise ValueError(init_type)

    # first init
    w = Wall(height=12)
    assert vars(w) == {'color': 'white', 'height': 12}

    # make sure this can be done a second time (since we replaced the __init__ method now)
    w = Wall(color='blue', height=1)
    assert vars(w) == {'color': 'blue', 'height': 1}


def test_init_partial_fields():
    class Wall(object):
        height = field(doc="Height of the wall in mm.")  # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str

        def post_init(self, foo='bar'):
            self.height
            print("post init man !")

        __init__ = make_init(height, post_init)

    #
    # assert str(signature(Wall.__init__)) == "(self, height, foo='bar')"

    # first init
    w = Wall(12)
    assert vars(w) == {'height': 12}  # color not initialized yet

    # make sure this can be done a second time (since we replaced the __init__ method now)
    w = Wall(foo='blue', height=1)
    assert vars(w) == {'height': 1}  # color not initialized yet
