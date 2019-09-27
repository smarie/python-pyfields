import pytest
from pyfields import field, MandatoryFieldInitError, with_fields, make_init


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
        w.height
    assert str(exc_info.value).startswith("Mandatory field 'height' has not been initialized yet on instance <")

    w.height = 12
    assert vars(w) == {'color': 'white', 'height': 12}


def test_readme_make_init_full_defaults():
    class Wall:
        height = field(doc="Height of the wall in mm.")           # type: int
        color = field(default='white', doc="Color of the wall.")  # type: str
        __init__ = make_init()

    # create an instance
    help(Wall)
    with pytest.raises(TypeError) as exc_info:
        w = Wall()
    assert str(exc_info.value).startswith("__init__()")

    help(Wall)

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

