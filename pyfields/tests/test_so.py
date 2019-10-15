#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import pytest

from pyfields import field, init_fields, make_init
from valid8 import ValidationError
from valid8.validation_lib import is_in


def test_so0(capsys):
    """ Checks answer at """

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
