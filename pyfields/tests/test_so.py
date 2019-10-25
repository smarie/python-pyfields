#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

import pytest

from pyfields import ReadOnlyFieldError, MandatoryFieldInitError, FieldTypeError
from pyfields.core import DescriptorClassField
from valid8 import ValidationError


def test_so0(capsys):
    """ Checks answer at https://stackoverflow.com/a/58344434/7262247 """

    from pyfields import field, init_fields

    with capsys.disabled():
        class C(object):
            x = field(default=None, doc="the optional 'x' property")
            y = field(doc="the mandatory 'y' property")
            z = field(doc="the mandatory 'z' property")

            @init_fields
            def __init__(self):
                pass

    c = C(y=1, z=2)
    print(vars(c))

    with capsys.disabled():
        out, err = capsys.readouterr()
        print(out)
        # assert out == """{'y': 1, 'x': None, 'z': 2}\n"""
        assert vars(c) == {'y': 1, 'x': None, 'z': 2}


def test_so1(capsys):
    """ Checks answer at https://stackoverflow.com/a/58344853/7262247 """

    from pyfields import field, init_fields

    class Account(object):
        first = field(doc="first name")
        last = field(doc="last name")
        age = field(doc="the age in years")
        id = field(doc="an identifier")
        balance = field(doc="current balance in euros")

        @init_fields
        def __init__(self, msg):
            print(msg)

    a = Account("hello, world!", first="s", last="marie", age=135, id=0, balance=-200000)
    print(vars(a))
    with capsys.disabled():
        out, err = capsys.readouterr()
        print(out)
        assert out.splitlines()[0] == "hello, world!"
        assert vars(a) == {'age': 135, 'balance': -200000, 'last': 'marie', 'id': 0, 'first': 's'}


def test_so2():
    """ Checks that answer at https://stackoverflow.com/a/58383062/7262247 is ok """

    from pyfields import field

    class Position(object):
        x = field(validators=lambda x: x > 0)
        y = field(validators={'y should be between 0 and 100': lambda y: y > 0 and y < 100})

    p = Position()
    p.x = 1
    with pytest.raises(ValidationError) as exc_info:
        p.y = 101
    qualname = Position.__dict__['y'].qualname
    assert str(exc_info.value) == "Error validating [%s=101]. " \
                                  "InvalidValue: y should be between 0 and 100. " \
                                  "Function [<lambda>] returned [False] for value 101." % qualname


def test_so3():
    """https://stackoverflow.com/a/58391645/7262247"""

    from pyfields import field

    class Spam(object):
        description = field(validators={"description can not be empty": lambda s: len(s) > 0})
        value = field(validators={"value must be greater than zero": lambda x: x > 0})

    s = Spam()
    with pytest.raises(ValidationError) as exc_info:
        s.description = ""
    qualname = Spam.__dict__['description'].qualname
    assert str(exc_info.value) == "Error validating [%s='']. " \
                                  "InvalidValue: description can not be empty. " \
                                  "Function [<lambda>] returned [False] for value ''." % qualname


def test_so4():
    """check https://stackoverflow.com/a/58394381/7262247"""

    from pyfields import field, init_fields
    from valid8.validation_lib import is_in

    ALLOWED_COLORS = ('blue', 'yellow', 'brown')

    class Car(object):
        """ My class with many fields """
        color = field(type_hint=str, check_type=True, validators=is_in(ALLOWED_COLORS))
        name = field(type_hint=str, check_type=True, validators={'should be non-empty': lambda s: len(s) > 0})
        wheels = field(type_hint=int, check_type=True, validators={'should be positive': lambda x: x > 0})

        @init_fields
        def __init__(self, msg="hello world!"):
            print(msg)

    c = Car(color='blue', name='roadie', wheels=3)
    assert vars(c) == {'_wheels': 3, '_name': 'roadie', '_color': 'blue'}

    qualname = Car.__dict__['wheels'].qualname

    with pytest.raises(TypeError) as exc_info:
        c.wheels = 'hello'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type %r. " \
                                  "Instead, received a 'str': 'hello'" % (qualname, int)

    with pytest.raises(ValidationError) as exc_info:
        c.wheels = 0
    assert str(exc_info.value) == "Error validating [%s=0]. " \
                                  "InvalidValue: should be positive. " \
                                  "Function [<lambda>] returned [False] for value 0." % qualname


def test_so5():
    """https://stackoverflow.com/a/58395677/7262247"""

    from pyfields import field, copy_value, init_fields
    from valid8.validation_lib import is_in

    class Well(object):
        name = field()                                        # Required
        group = field()                                       # Required
        operate_list = field(default_factory=copy_value([]))  # Optional
        monitor_list = field(default_factory=copy_value([]))  # Optional
        geometry = field(default=None)                        # Optional
        perf = field(default=None)                            # Optional

    valid_types = ('type_A', 'type_B')

    class Operate(object):
        att = field()                                  # Required
        type_ = field(type_hint=str, check_type=True, validators=is_in(valid_types))   # Required
        value = field(default_factory=copy_value([]))  # Optional
        mode = field(default=None)                     # Optional
        action = field(default=None)                   # Optional

        @init_fields
        def __init__(self):
            pass

    o = Operate(att="foo", type_='type_A')

    with pytest.raises(TypeError):
        o.type_ = 1  # <-- raises TypeError: Invalid value type provided

    with pytest.raises(ValidationError):
        bad_o = Operate(att="foo", type_='type_WRONG')  # <-- raises ValidationError: NotInAllowedValues: x in ('type_A', 'type_B') does not hold for x=type_WRONG


def test_so6():
    """checks that answer at https://stackoverflow.com/a/58396678/7262247 works"""
    from pyfields import field, init_fields

    class Position(object):
        x = field(type_hint=int, check_type=True, validators=lambda x: x > 0)
        y = field(type_hint=int, check_type=True, validators={'y should be between 0 and 100': lambda y: y > 0 and y < 100})

        @init_fields
        def __init__(self, msg="hello world!"):
            print(msg)

    p = Position(x=1, y=12)
    with pytest.raises(TypeError) as exc_info:
        p.x = '1'
    qualname = Position.__dict__['x'].qualname
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type %r. Instead, received a 'str': '1'" % (qualname, int)

    with pytest.raises(ValidationError) as exc_info:
        p.y = 101


def test_so7():
    """ checks answer at https://stackoverflow.com/a/58432813/7262247 """

    from pyfields import field

    class User(object):
        username = field(read_only=True, validators={'should contain more than 2 characters': lambda s: len(s) > 2})

    u = User()
    u.username = "earthling"
    assert vars(u) == {'_username': "earthling"}
    with pytest.raises(ReadOnlyFieldError) as exc_info:
        u.username = "earthling2"
    qualname = User.__dict__['username'].qualname
    assert str(exc_info.value) == "Read-only field '%s' has already been initialized on instance %s and cannot be " \
                                  "modified anymore." % (qualname, u)


def test_so8_classfields():
    """ checks answer at xxx (todo: not capable of doing this yet) """

    from pyfields import classfield

    class A(object):
        s = classfield(type_hint=int, check_type=True)

    class ClassFromA(A):
        pass

    s_field = A.__dict__['s']
    assert isinstance(s_field, DescriptorClassField)

    for c in (A, ClassFromA):
        with pytest.raises(MandatoryFieldInitError):
            print(c.s)

        with pytest.raises(FieldTypeError):
            c.s = "hello"
