#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys
from inspect import isdatadescriptor, ismethoddescriptor

try:
    from typing import Union, Callable, Type, Any, TypeVar
    DecoratedClass = TypeVar("DecoratedClass", bound=Type[Any])
except ImportError:
    pass


from pyfields import Field, field, make_init as mkinit, copy_value


PY36 = sys.version_info >= (3, 6)


def autofields(check_types=False,     # type: Union[bool, DecoratedClass]
               include_upper=False,   # type: bool
               include_dunder=False,  # type: bool
               make_init=True         # type: bool
               ):
    # type: (...) -> Union[Callable[[DecoratedClass], DecoratedClass], DecoratedClass]
    """
    Decorator to automatically create fields and constructor on a class.

    When a class is decorated with `@autofields`, all of its members are automatically transformed to fields.
    More precisely: members that only contain a type annotation become mandatory fields, while members that contain a
    value (with or without type annotation) become optional fields with a `copy_value` default_factory.

    By default, the following members are NOT transformed into fields:

     * members with upper-case names. This is because this kind of name formatting usually denotes class constants. They
       can be transformed to fields by setting `include_upper=True`.
     * members with dunder-like names. They can be included using `include_dunder=True`. Note that reserved python
       dunder names such as `__name__`, `__setattr__`, etc. can not be transformed to fields, even when
       `include_dunder=True`.
     * members that are classes or methods defined in the class (that is, where their `.__name__` is the same name than
       the member name).
     * members that are already fields. Therefore you can continue to use `field()` on certain members explicitly if
       you need to add custom validators, converters, etc.

    All created fields have their `type_hint` filled with the type hint associated with the member, and have
    `check_type=False` by default. This can be changed by setting `check_types=True`.

    Finally, in addition, an init method (constructor) is generated for the class, using `make_init()`. This may be
    disabled by setting `make_init=False`..

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6): pytest.skip("doctest skipped for python < 3.6")
    ...
    >>> @autofields
    ... class Pocket:
    ...     SENTENCE = "hello world"  # uppercase: not a field
    ...     size: int   # mandatory field
    ...     items = []  # optional - default value will be a factory
    ...
    >>> p = Pocket(size=10)
    >>> p.items
    []
    >>> Pocket(size=10, SENTENCE="hello")
    Traceback (most recent call last):
    ...
    TypeError: __init__() got an unexpected keyword argument 'SENTENCE'


    :param check_types: boolean flag (default: False) indicating the value of `check_type` for created fields. Note that
        the type hint of each created field is copied from the type hint of the member it originates from.
    :param include_upper: boolean flag (default: False) indicating whether upper-case class members should be also
        transformed to fields.
    :param include_dunder: boolean flag (default: False) indicating whether dunder-named class members should be also
        transformed to fields. Note that even if you set this to True, members with reserved python dunder names will
        not be transformed. See `is_reserved_dunder` for the list of reserved names.
    :param make_init: boolean flag (default: True) indicating whether a constructor should be created for the class if
        no `__init__` method is present. Such constructor will be created using `__init__ = make_init()`.
    :return:
    """
    def _autofields(cls):
        NO_DEFAULT = object()

        try:
            # Are type hints present ?
            cls_annotations = cls.__annotations__
        except AttributeError:
            # No type hints: shortcut. note: do not return a generator since we'll modify __dict__ in the loop after
            members_defs = tuple((k, None, v) for k, v in cls.__dict__.items())
        else:
            # Fill the list of potential fields definitions
            members_defs = []
            cls_dict = cls.__dict__

            if not PY36:
                # Is this even possible ? does not seem so. Raising an error until this is reported
                raise ValueError("Unsupported case: `__annotations__` is present while python is < 3.6 - please report")
            #     # dont care about the order, it is not preserved
            #     # -- fields with type hint
            #     for member_name, type_hint in cls_annotations.items():
            #         members_defs.append((member_name, type_hint, cls_dict.get(member_name, NO_DEFAULT)))
            #
            #     # -- fields without type hint
            #     members_with_type = set(cls_annotations.keys())
            #     for member_name, default_value in cls_dict.items():
            #         if member_name not in members_with_type:
            #             members_defs.append((member_name, None, default_value))
            #
            else:
                # create a list of members with consistent order
                members_with_type_and_value = set(cls_annotations.keys()).intersection(cls_dict.keys())

                in_types = [name for name in cls_annotations if name in members_with_type_and_value]
                in_values = [name for name in cls_dict if name in members_with_type_and_value]
                assert in_types == in_values

                def t_gen():
                    """ generator used to fill the definitions for members only in annotations dict """
                    next_stop_name = yield
                    for _name, _type_hint in cls_annotations.items():
                        if _name != next_stop_name:
                            members_defs.append((_name, _type_hint, NO_DEFAULT))
                        else:
                            next_stop_name = yield

                def v_gen():
                    """ generator used to fill the definitions for members only in the values dict """
                    next_stop_name, next_stop_type_hint = yield
                    for _name, _default_value in cls_dict.items():
                        if _name != next_stop_name:
                            members_defs.append((_name, None, _default_value))
                        else:
                            members_defs.append((_name, next_stop_type_hint, _default_value))
                            next_stop_name, next_stop_type_hint = yield

                types_gen = t_gen()
                types_gen.send(None)
                values_gen = v_gen()
                values_gen.send(None)
                for common_name in in_types:
                    types_gen.send(common_name)
                    values_gen.send((common_name, cls_annotations[common_name]))
                # last one
                try:
                    types_gen.send(None)
                except StopIteration:
                    pass
                try:
                    values_gen.send((None, None))
                except StopIteration:
                    pass

        # Main loop : for each member, possibly create a field()
        for member_name, type_hint, default_value in members_defs:
            if not include_upper and member_name == member_name.upper():
                # excluded uppercase
                continue
            elif (include_dunder and is_reserved_dunder(member_name)) \
                    or is_dunder(member_name):
                # excluded dunder
                continue
            elif isinstance(default_value, Field):
                # already a field, no need to create
                # but in order to preserve relative order with generated fields, detach and attach again
                try:
                    delattr(cls, member_name)
                except AttributeError:
                    pass
                setattr(cls, member_name, default_value)
                continue
            elif isinstance(default_value, property) or isdatadescriptor(default_value) \
                    or ismethoddescriptor(default_value):
                # a property or a data or non-data descriptor > exclude
                continue
            elif (isinstance(default_value, type) or callable(default_value)) \
                    and getattr(default_value, '__name__', None) == member_name:
                # a function/class defined in the class > exclude
                continue
            else:
                # Create a field !!
                need_to_check_type = check_types and (type_hint is not None)
                if default_value is NO_DEFAULT:
                    # mandatory field
                    new_field = field(check_type=need_to_check_type)
                else:
                    # optional field : copy the default value by default
                    new_field = field(check_type=need_to_check_type, default_factory=copy_value(default_value))

                # Attach the newly created field to the class. Delete attr first so that order is preserved
                # even if one of them had only an annotation.
                try:
                    delattr(cls, member_name)
                except AttributeError:
                    pass
                setattr(cls, member_name, new_field)
                new_field.set_as_cls_member(cls, member_name, type_hint=type_hint)

        # Finally, make init if not already explicitly present
        if make_init and ('__init__' not in cls.__dict__):
            new_init = mkinit()
            cls.__init__ = new_init
            # attach explicitly to the class so that the descriptor is correctly completed.
            new_init.__set_name__(cls, '__init__')

        return cls
    # end of _autofields(cls)

    # Main logic of autofield(**kwargs)
    if check_types is not True and check_types is not False and isinstance(check_types, type):
        # called without arguments @autofields: check_types is the decorated class
        assert include_upper is False
        assert include_dunder is False
        # use the parameter and use the correct check_types default value now
        _cls = check_types
        check_types = False  # <-- important: variable is in the local context of _autofields
        return _autofields(cls=_cls)
    else:
        # called with arguments @autofields(...): return the decorator
        return _autofields


def is_dunder(name):
    return len(name) >= 4 and name.startswith('__') and name.endswith('__')


def is_reserved_dunder(name):
    return name in ('__doc__', '__name__', '__qualname__', '__module__', '__code__', '__globals__',
                    '__dict__', '__closure__', '__annotations__')  # '__defaults__', '__kwdefaults__')
