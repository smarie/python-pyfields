#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import pytest
import dataclasses as dc
from attr import attrs, attrib

from pyfields import field, with_fields


def _create_class_creator(type):
    if type == "pyfields":
        def _call_me():
            class Wall(object):
                height = field(doc="Height of the wall in mm.")  # type: int
                color = field(default='white', doc="Color of the wall.")  # type: str

                @with_fields
                def __init__(self, fields):
                    fields.init(self)
            return Wall

    elif type == "python":
        def _call_me():
            class Wall(object):
                def __init__(self,
                             height,        # type: int
                             color='white'   # type: str
                             ):
                    """

                    :param height: Height of the wall in mm.
                    :param color: Color of the wall.
                    """
                    self.height = height
                    self.color = color
            return Wall
    elif type == "attrs":
        def _call_me():
            @attrs
            class Wall(object):
                height: int = attrib(repr=False, cmp=False, hash=False)
                color: str = attrib(default='white', repr=False, cmp=False, hash=False)

            return Wall

    elif type == "dataclass":
        def _call_me():
            @dc.dataclass
            class Wall(object):
                height: int = dc.field(init=True)
                color: str = dc.field(default='white', init=True)

            return Wall
    else:
        raise ValueError()

    return _call_me


@pytest.mark.parametrize("type", ["python", "pyfields", "attrs", "dataclass"])
def test_timers_class(benchmark, type):
    # benchmark it
    benchmark(_create_class_creator(type))


def _instantiate(clazz):
    return lambda: clazz(color='hello', height=50)


@pytest.mark.parametrize("type", ["python", "pyfields", "attrs", "dataclass"])
def test_timers_instance(benchmark, type):
    clazz = _create_class_creator(type)()

    benchmark(_instantiate(clazz))


def _read_field(obj):
    return lambda: obj.color


@pytest.mark.parametrize("type", ["python", "pyfields", "attrs", "dataclass"])
def test_timers_instance_read(benchmark, type):
    clazz = _create_class_creator(type)()
    obj = clazz(color='hello', height=50)

    benchmark(_read_field(obj))


def _write_field(obj):
    obj.color = 'sky_blue'


@pytest.mark.parametrize("type", ["python", "pyfields", "attrs", "dataclass"])
def test_timers_instance_write(benchmark, type):
    clazz = _create_class_creator(type)()
    obj = clazz(color='hello', height=50)

    benchmark(_write_field, obj)
