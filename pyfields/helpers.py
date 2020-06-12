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


class NotAFieldError(TypeError):
    """ Raised by `get_field` when the class member with that name is not a field """
    __slots__ = 'name', 'cls'

    def __init__(self, cls, name):
        self.name = name
        self.cls = cls


def get_field(cls, name):
    """
    Utility method to return the field member with name `name` in class `cls`.
    If the member is not a field, a `NotAFieldError` is raised.

    :param cls:
    :param name:
    :return:
    """
    try:
        member = getattr(cls, name)
    except ClassFieldAccessError as e:
        # we know it is a field :)
        return e.field
    except Exception:
        # any other exception that can happen with a descriptor for example
        raise NotAFieldError(cls, name)
    else:
        # it is a field if is it an instance of Field
        if isinstance(member, Field):
            return member
        else:
            raise NotAFieldError(cls, name)


def yield_fields(cls,
                 include_inherited=True,  # type: bool
                 remove_duplicates=True,  # type: bool
                 ancestors_first=True,    # type: bool
                 _auto_fix_fields=False   # type: bool
                 ):
    """
    Similar to `get_fields` but as a generator.

    :param cls:
    :param include_inherited:
    :param remove_duplicates:
    :param ancestors_first:
    :param _auto_fix_fields:
    :return:
    """
    # List the classes where we should be looking for fields
    if include_inherited:
        where_cls = reversed(getmro(cls)) if ancestors_first else getmro(cls)
    else:
        where_cls = (cls,)

    # Init
    _already_found_names = set() if remove_duplicates else None  # a reference set of already yielded field names
    _cls_pep484_member_type_hints = None                         # where to hold found type hints if needed
    _all_fields_for_cls = None                                   # temporary list when we have to reorder

    # finally for each class, gather all fields in order
    for _cls in where_cls:
        if not PY36:
            # in python < 3.6 we'll need to sort the fields at the end as class member order is not preserved
            _all_fields_for_cls = []
        elif _auto_fix_fields:
            # in python >= 3.6, pep484 type hints can be available as member annotation, grab them
            _cls_pep484_member_type_hints = get_type_hints(_cls)

        for member_name in vars(_cls):
            # if not member_name.startswith('__'):   not stated in the doc: too dangerous to have such implicit filter

            # avoid infinite recursion as this method is called in the descriptor for __init__
            if not member_name == '__init__':
                try:
                    field = get_field(_cls, member_name)
                except NotAFieldError:
                    continue

                if _auto_fix_fields:
                    # take this opportunity to set the name and type hints
                    field.set_as_cls_member(_cls, member_name, owner_cls_type_hints=_cls_pep484_member_type_hints)

                if remove_duplicates:
                    if member_name in _already_found_names:
                        continue
                    else:
                        _already_found_names.add(member_name)

                # maybe the field is overridden, in that case we should directly yield the new one
                if _cls is not cls:
                    try:
                        overridden_field = get_field(cls, member_name)
                    except NotAFieldError:
                        overridden_field = None
                else:
                    overridden_field = None

                # finally yield it...
                if PY36:  # ...immediately in recent python versions because order is correct already
                    yield field if overridden_field is None else overridden_field
                else:     # ...or wait for this class to be collected, because the order needs to be fixed
                    _all_fields_for_cls.append((field, overridden_field))

        if not PY36:
            # order is random in python < 3.6 - we need to explicitly sort according to instance creation number
            _all_fields_for_cls.sort(key=lambda f: f[0].__fieldinstcount__)
            for field, overridden_field in _all_fields_for_cls:
                yield field if overridden_field is None else overridden_field


def has_fields(cls,
               include_inherited=True  # type: bool
               ):
    """
    Returns True if class `cls` defines at least one `pyfields` field.
    If `include_inherited` is `True` (default), the method will return `True` if at least a field is defined in the
    class or one of its ancestors. If `False`, the fields need to be defined on the class itself.

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

    By default duplicates are removed and ancestor fields are included and appear first. If a field is overridden,
    it will appear at the position of the overridden field in the order.

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

    # attach a method to easily get a new factory with a new value
    def get_copied_value():
        return val

    def clone_with_new_val(newval):
        return copy_value(newval, deep)

    create_default.get_copied_value = get_copied_value
    create_default.clone_with_new_val = clone_with_new_val
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
