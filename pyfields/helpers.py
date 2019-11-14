#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
from copy import copy, deepcopy
from inspect import getmro

try:
    from typing import Union, Type, TypeVar
    T = TypeVar('T')
except ImportError:
    pass

from pyfields.core import Field, ClassFieldAccessError, PY36, get_type_hints


def yield_fields(cls,
                 include_inherited=True,  # type: bool
                 remove_duplicates=True,  # type: bool
                 ancestors_first=True,    # type: bool
                 _auto_fix_fields=False   # type: bool
                 ):
    """

    :param cls:
    :param include_inherited:
    :param remove_duplicates:
    :param ancestors_first:
    :param _auto_fix_fields:
    :return:
    """
    names = set()

    # list the classes where we should be looking for fields
    if include_inherited:
        where_cls = reversed(getmro(cls)) if ancestors_first else getmro(cls)
    else:
        where_cls = (cls,)

    # finally for each class, gather all fields in order
    _cls_pep484_member_type_hints, res_for_cls = None, None
    for _cls in where_cls:
        if not PY36:
            # in python < 3.6 we'll need to sort the fields at the end as class member order is not preserved
            res_for_cls = []
        elif _auto_fix_fields:
            # in python >= 3.6, pep484 type hints can be available as member annotation, grab them
            _cls_pep484_member_type_hints = get_type_hints(_cls)

        for member_name in vars(_cls):
            # if not member_name.startswith('__'):   not stated in the doc: too dangerous to have such implicit filter

            # avoid infinite recursion as this method is called in the descriptor for __init__
            if not member_name == '__init__':
                try:
                    member = getattr(_cls, member_name)
                except ClassFieldAccessError as e:
                    # we know it is a field :)
                    _is_field = True
                    member = e.field
                else:
                    # it is a field if instance of Field
                    _is_field = isinstance(member, Field)

                if _is_field:
                    if _auto_fix_fields:
                        # take this opportunity to set the name and type hints
                        member.set_as_cls_member(_cls, member_name, _cls_pep484_member_type_hints)
                    if remove_duplicates:
                        if member_name in names:
                            continue
                        else:
                            names.add(member_name)

                    # maybe the field is overriden, in that case we should directly yield the new one
                    if _cls is not cls:
                        try:
                            overridden_member = getattr(cls, member_name)
                        except ClassFieldAccessError as e:
                            member = e.field
                        else:
                            if isinstance(overridden_member, Field):
                                member = overridden_member

                    # finally yield it
                    if not PY36:
                        res_for_cls.append(member)
                    else:
                        yield member

        if not PY36:
            # order is random in python < 3.6 - we need to explicitly sort according to instance creation number
            res_for_cls.sort(key=lambda f: f.__fieldinstcount__)
            for m in res_for_cls:
                yield m


def has_fields(cls,
               include_inherited=True  # type: bool
               ):
    """
    Returns True if class `cls` defines at least one `pyfields` field

    :param cls:
    :param include_inherited:
    :return:
    """
    return any(yield_fields(cls, include_inherited=include_inherited))


def get_fields(cls,
               include_inherited=True,  # type: bool
               remove_duplicates=True,  # type: bool
               ancestors_first=True,    # type: bool
               container_type=tuple,    # type: Type[T]
               _auto_fix_fields=False   # type: bool
               ):
    # type: (...) -> T
    """
    Utility method to collect all fields defined in a class, including all inherited or not.

    :param cls:
    :param include_inherited:
    :param remove_duplicates:
    :param ancestors_first:
    :param container_type:
    :param _auto_fix_fields:
    :return: the fields (by default, as a tuple)
    """
    return container_type(yield_fields(cls, include_inherited=include_inherited,
                                       remove_duplicates=remove_duplicates, ancestors_first=ancestors_first,
                                       _auto_fix_fields=_auto_fix_fields))


# def ordered_dir(cls,
#                 ancestors_first=False  # type: bool
#                 ):
#     """
#     since `dir` does not preserve order, lets have our own implementation
#
#     :param cls:
#     :param ancestors_first:
#     :return:
#     """
#     classes = reversed(getmro(cls)) if ancestors_first else getmro(cls)
#
#     for _cls in classes:
#         for k in vars(_cls):
#             yield k


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
