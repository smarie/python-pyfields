#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
from copy import copy, deepcopy

try:
    from typing import Union
except ImportError:
    pass

from pyfields.core import Field


def copy_value(val,
               deep=True  # type: bool
               ):
    """
    Returns a default value factory to be used in a `field(default_factory=...)`.

    That factory will create a copy of the provided `val` everytime it is called. Handy if you wish to use mutable
    objects as default values for your fields ; for example lists.

    :param val: the (mutable) value to copy
    :param deep: by default deep copies will be created. You can change this behaviour by setting this to `False`
    :return:
    """
    if deep:
        def create_default(obj):
            return deepcopy(val)
    else:
        def create_default(obj):
            return copy(val)

    return create_default


def copy_field(field_or_name,  # type: Union[str, Field]
               deep=True       # type: bool
               ):
    """
    Returns a default value factory to be used in a `field(default_factory=...)`.

    That factory will create a copy of the value in the given field. You can provide a field or a field name, in which
    case this method is strictly equivalent to `copy_attr`.

    :param field_or_name: the field or name of the field for which the value needs to be copied
    :param deep: by default deep copies will be created. You can change this behaviour by setting this to `False`
    :return:
    """
    if isinstance(field_or_name, Field):
        if field_or_name.name is None:
            # Name not yet available, we'll get it later
            if deep:
                def create_default(obj):
                    return deepcopy(getattr(obj, field_or_name.name))
            else:
                def create_default(obj):
                    return copy(getattr(obj, field_or_name.name))

            return create_default
        else:
            # use the field name
            return copy_attr(field_or_name.name, deep=deep)
    else:
        # this is already a field name
        return copy_attr(field_or_name, deep=deep)


def copy_attr(attr_name,  # type: str
              deep=True   # type: bool
              ):
    """
    Returns a default value factory to be used in a `field(default_factory=...)`.

    That factory will create a copy of the value in the given attribute.

    :param attr_name: the name of the attribute for which the value will be copied
    :param deep: by default deep copies will be created. You can change this behaviour by setting this to `False`
    :return:
    """
    if deep:
        def create_default(obj):
            return deepcopy(getattr(obj, attr_name))
    else:
        def create_default(obj):
            return copy(getattr(obj, attr_name))

    return create_default
