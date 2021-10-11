# Authors: Sylvain MARIE <sylvain.marie@se.com>
#          + All contributors to <https://github.com/smarie/python-pyfields>
#
# License: 3-clause BSD, <https://github.com/smarie/python-pyfields/blob/master/LICENSE>
import sys
from copy import deepcopy
from inspect import isdatadescriptor, ismethoddescriptor

try:
    from typing import Union, Callable, Type, Any, TypeVar, Tuple, Iterable
    DecoratedClass = TypeVar("DecoratedClass", bound=Type[Any])
except ImportError:
    pass


from .core import Field, field
from .init_makers import make_init as mkinit
from .helpers import copy_value, get_fields


PY36 = sys.version_info >= (3, 6)
DEFAULT_EXCLUDED = ('_abc_impl',)


def _make_init(cls):
    """Utility method used in autofields and autoclass to create the constructor based on the class fields"""
    if "__init__" not in cls.__dict__:
        new_init = mkinit()
        cls.__init__ = new_init
        # attach explicitly to the class so that the descriptor is correctly completed.
        new_init.__set_name__(cls, '__init__')


def autofields(check_types=False,         # type: Union[bool, DecoratedClass]
               include_upper=False,       # type: bool
               include_dunder=False,      # type: bool
               exclude=DEFAULT_EXCLUDED,  # type: Iterable[str]
               make_init=True,            # type: bool
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


    :param check_types: boolean flag (default: `False`) indicating the value of `check_type` for created fields. Note
        that the type hint of each created field is copied from the type hint of the member it originates from.
    :param include_upper: boolean flag (default: `False`) indicating whether upper-case class members should be also
        transformed to fields (usually such names are reserved for class constants, not for fields).
    :param include_dunder: boolean flag (default: `False`) indicating whether dunder-named class members should be also
        transformed to fields. Note that even if you set this to True, members with reserved python dunder names will
        not be transformed. See `is_reserved_dunder` for the list of reserved names.
    :param exclude: a tuple of field names that should be excluded from automatic creation. By default this is set to
        `DEFAULT_EXCLUDED`, which eliminates fields created by `ABC`.
    :param make_init: boolean flag (default: `True`) indicating whether a constructor should be created for the class if
        no `__init__` method is present. Such constructor will be created using `__init__ = make_init()`.
    :return:
    """
    def _autofields(cls):
        NO_DEFAULT = object()

        try:
            # Are type hints present ?
            # note: since this attribute can be inherited, we get the own attribute only
            # cls_annotations = cls.__annotations__
            cls_annotations = getownattr(cls, "__annotations__")
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
            if member_name in exclude:
                # excluded explicitly
                continue
            elif not include_upper and member_name == member_name.upper():
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
                    try:
                        # autocheck: make sure that we will be able to create copies later
                        deepcopy(default_value)
                    except Exception as e:
                        raise ValueError("The provided default value for field %r=%r can not be deep-copied: "
                                         "caught error %r" % (member_name, default_value, e))
                    new_field = field(check_type=need_to_check_type,
                                      default_factory=copy_value(default_value, autocheck=False))

                # Attach the newly created field to the class. Delete attr first so that order is preserved
                # even if one of them had only an annotation.
                try:
                    delattr(cls, member_name)
                except AttributeError:
                    pass
                setattr(cls, member_name, new_field)
                new_field.set_as_cls_member(cls, member_name, type_hint=type_hint)

        # Finally, make init if not already explicitly present
        if make_init:
            _make_init(cls)

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


_dict, _hash = dict, hash
"""Aliases for autoclass body"""


def autoclass(
    # --- autofields
    fields=True,                  # type: Union[bool, DecoratedClass]
    typecheck=False,              # type: bool
    # --- constructor
    init=True,                    # type: bool
    # --- class methods
    dict=True,                    # type: bool
    dict_public_only=True,        # type: bool
    repr=True,                    # type: bool
    repr_curly_mode=False,        # type: bool
    repr_public_only=True,        # type: bool
    eq=True,                      # type: bool
    eq_public_only=False,         # type: bool
    hash=True,                    # type: bool
    hash_public_only=False,       # type: bool
    # --- advanced
    af_include_upper=False,       # type: bool
    af_include_dunder=False,      # type: bool
    af_exclude=DEFAULT_EXCLUDED,  # type: Iterable[str]
    ac_include=None,              # type: Union[str, Tuple[str]]
    ac_exclude=None,              # type: Union[str, Tuple[str]]
):
    """
    A decorator to automate many things at once for your class.

    First if `fields=True` (default) it executes `@autofields` to generate fields from attribute defined at class
    level.

     - you can include attributes with dunder names or uppercase names with `af_include_dunder` and
       `af_include_upper` respectively
     - you can enable type checking on all fields at once by setting `check_types=True`
     - the constructor is not generated at this stage

    Then it generates methods for the class:

     - if `init=True` (default) it generates the constructor based on all fields present, using `make_init()`.
     - if `dict=True` (default) it generates `to_dict` and `from_dict` methods. Only public fields are represented in
       `to_dict`, you can change this with `dict_public_only=False`.
     - if `repr=True` (default) it generates a `__repr__` method. Only public fields are represented, you can change
       this with `repr_public_only=False`.
     - if `eq=True` (default) it generates an `__eq__` method, so that instances can be compared to other instances and
       to dicts. All fields are compared by default, you can change this with `eq_public_only=True`.
     - if `hash=True` (default) it generates an `__hash__` method, so that instances can be inserted in sets or dict
       keys. All fields are hashed by default, you can change this with `hash_public_only=True`.

    You can specify an explicit list of fields to include or exclude in the dict/repr/eq/hash methods with the
    `ac_include` and `ac_exclude` parameters.

    Note that this decorator is similar to the [autoclass library](https://smarie.github.io/python-autoclass/) but is
    reimplemented here. In particular the parameter names and dictionary behaviour are different.

    :param fields: boolean flag (default: True) indicating whether to create fields automatically. See `@autofields`
        for details
    :param typecheck: boolean flag (default: False) used when fields=True indicating the value of `check_type`
        for created fields. Note that the type hint of each created field is copied from the type hint of the member it
        originates from.
    :param init: boolean flag (default: True) indicating whether a constructor should be created for the class if
        no `__init__` method is already present. Such constructor will be created using `__init__ = make_init()`.
        This is the same behaviour than `make_init` in `@autofields`. Note that this is *not* automatically disabled if
        you set `fields=False`.
    :param dict: a boolean to automatically create `cls.from_dict(dct)` and `obj.to_dict()` methods on the class
        (default: True).
    :param dict_public_only: a boolean (default: True) to indicate if only public fields should be
        exposed in the dictionary view created by `to_dict` when `dict=True`.
    :param repr: a boolean (default: True) to indicate if `__repr__` and `__str__` should be created for the class if
        not explicitly present.
    :param repr_curly_mode: a boolean (default: False) to turn on an alternate string representation when `repr=True`,
        using curly braces.
    :param repr_public_only: a boolean (default: True) to indicate if only public fields should be
        exposed in the string representation when `repr=True`.
    :param eq: a boolean (default: True) to indicate if `__eq__` should be created for the class if not explicitly
        present.
    :param eq_public_only: a boolean (default: False) to indicate if only public fields should be
        compared in the equality method created when `eq=True`.
    :param hash: a boolean (default: True) to indicate if `__hash__` should be created for the class if not explicitly
        present.
    :param hash_public_only: a boolean (default: False) to indicate if only public fields should be
        hashed in the hash method created when `hash=True`.
    :param af_include_upper: boolean flag (default: False) used when autofields=True indicating whether
        upper-case class members should be also transformed to fields (usually such names are reserved for class
        constants, not for fields).
    :param af_include_dunder: boolean flag (default: False) used when autofields=True indicating whether
        dunder-named class members should be also transformed to fields. Note that even if you set this to True,
        members with reserved python dunder names will not be transformed. See `is_reserved_dunder` for the list of
        reserved names.
    :param af_exclude: a tuple of explicit attribute names to exclude from automatic fields creation. See
        `@autofields(exclude=...)` for details.
    :param ac_include: a tuple of explicit attribute names to include in dict/repr/eq/hash (None means all)
    :param ac_exclude: a tuple of explicit attribute names to exclude in dict/repr/eq/hash. In such case,
        include should be None.
    :return:
    """
    if not fields and (af_include_dunder or af_include_upper or typecheck):
        raise ValueError("Not able to set af_include_dunder or af_include_upper or typecheck when fields=False")

    # switch between args and actual symbols for readability
    dict_on = dict
    dict = _dict
    hash_on = hash
    hash = _hash

    # Create the decorator function
    def _apply_decorator(cls):

        # create fields automatically
        if fields:
            cls = autofields(check_types=typecheck, include_upper=af_include_upper,
                             exclude=af_exclude, include_dunder=af_include_dunder, make_init=False)(cls)

        # make init if not already explicitly present
        if init:
            _make_init(cls)

        # list all fields
        all_pyfields = get_fields(cls)
        if len(all_pyfields) == 0:
            raise ValueError("No fields detected on class %s (including inherited ones)" % cls)

        # filter selected
        all_names = tuple(f.name for f in all_pyfields)
        selected_names = filter_names(all_names, include=ac_include, exclude=ac_exclude, caller="@autoclass")
        public_selected_names = tuple(n for n in selected_names if not n.startswith('_'))

        # to/from dict
        if dict_on:
            dict_names = public_selected_names if dict_public_only else selected_names
            if "to_dict" not in cls.__dict__:

                def to_dict(self):
                    """ Generated by @pyfields.autoclass based on the class fields """
                    return {n: getattr(self, n) for n in dict_names}

                cls.to_dict = to_dict
            if "from_dict" not in cls.__dict__:

                def from_dict(cls, dct):
                    """ Generated by @pyfields.autoclass """
                    return cls(**dct)

                cls.from_dict = classmethod(from_dict)

        # __str__ and __repr__
        if repr:
            repr_names = public_selected_names if repr_public_only else selected_names
            if not repr_curly_mode:  # default

                def __repr__(self):
                    """ Generated by @pyfields.autoclass based on the class fields """
                    return '%s(%s)' % (self.__class__.__name__,
                                       ', '.join('%s=%r' % (k, getattr(self, k)) for k in repr_names))
            else:
                def __repr__(self):
                    """ Generated by @pyfields.autoclass based on the class fields """
                    return '%s(**{%s})' % (self.__class__.__name__,
                                           ', '.join('%r: %r' % (k, getattr(self, k)) for k in repr_names))

            if "__repr__" not in cls.__dict__:
                cls.__repr__ = __repr__
            if "__str__" not in cls.__dict__:
                cls.__str__ = __repr__

        # __eq__
        if eq:
            eq_names = public_selected_names if eq_public_only else selected_names

            def __eq__(self, other):
                """ Generated by @pyfields.autoclass based on the class fields """
                if isinstance(other, dict):
                    # comparison with dicts only when a to_dict method is available
                    try:
                        _self_to_dict = self.to_dict
                    except AttributeError:
                        return False
                    else:
                        return _self_to_dict() == other
                elif isinstance(self, other.__class__):
                    # comparison with objects of the same class or a parent
                    try:
                        for att_name in eq_names:
                            if getattr(self, att_name) != getattr(other, att_name):
                                return False
                    except AttributeError:
                        return False
                    else:
                        return True
                elif isinstance(other, self.__class__):
                    # other is a subtype: call method on other
                    return other.__eq__(self)  # same as NotImplemented ?
                else:
                    # classes are not related: False
                    return False

            if "__eq__" not in cls.__dict__:
                cls.__eq__ = __eq__

        # __hash__
        if hash_on:
            hash_names = public_selected_names if hash_public_only else selected_names

            def __hash__(self):
                """ Generated by @autoclass. Implements the __hash__ method by hashing a tuple of field values """

                # note: Should we prepend a unique hash for the class as `attrs` does ?
                # return hash(tuple([type(self)] + [getattr(self, att_name) for att_name in added]))
                # > No, it seems more intuitive to not do that.
                # Warning: the consequence is that instances of subtypes will have the same hash has instance of their
                # parent class if they have all the same attribute values

                return hash(tuple(getattr(self, att_name) for att_name in hash_names))

            if "__hash__" not in cls.__dict__:
                cls.__hash__ = __hash__

        return cls

    # Apply: Decorator vs decorator factory logic
    if isinstance(fields, type):
        # called without parenthesis: directly apply decorator on first argument
        cls = fields
        fields = True  # set it back to its default value
        return _apply_decorator(cls)
    else:
        # called with parenthesis: return a decorator function
        return _apply_decorator


def filter_names(all_names,
                 include=None,  # type: Union[str, Tuple[str]]
                 exclude=None,  # type: Union[str, Tuple[str]]
                 caller=""      # type: str
                 ):
    # type: (...) -> Iterable[str]
    """
    Common validator for include and exclude arguments

    :param all_names:
    :param include:
    :param exclude:
    :param caller:
    :return:
    """
    if include is not None and exclude is not None:
        raise ValueError("Only one of 'include' or 'exclude' argument should be provided.")

    # check that include/exclude don't contain names that are incorrect
    selected_names = all_names
    if include is not None:
        if exclude is not None:
            raise ValueError('Only one of \'include\' or \'exclude\' argument should be provided.')

        # get the selected names and check that all names in 'include' are actually valid names
        included = (include,) if isinstance(include, str) else tuple(include)
        incorrect = set(included) - set(all_names)
        if len(incorrect) > 0:
            raise ValueError("`%s` definition exception: `include` contains %r that is/are "
                             "not part of %r" % (caller, incorrect, all_names))
        selected_names = included

    elif exclude is not None:
        excluded_set = {exclude} if isinstance(exclude, str) else set(exclude)
        incorrect = excluded_set - set(all_names)
        if len(incorrect) > 0:
            raise ValueError("`%s` definition exception: exclude contains %r that is/are "
                             "not part of %r" % (caller, incorrect, all_names))
        selected_names = tuple(n for n in all_names if n not in excluded_set)

    return selected_names


# def method_already_there(cls,
#                          method_name,           # type: str
#                          this_class_only=False  # type: bool
#                          ):
#     # type: (...) -> bool
#     """
#     Returns True if method `method_name` is already implemented by object_type, that is, its implementation differs
#     from the one in `object`.
#
#     :param cls:
#     :param method_name:
#     :param this_class_only:
#     :return:
#     """
#     if this_class_only:
#         return method_name in cls.__dict__  # or vars(cls)
#     else:
#         method = getattr(cls, method_name, None)
#         return method is not None and method is not getattr(object, method_name, None)


def getownattr(cls, attrib_name):
    """
    Return the value of `cls.<attrib_name>` if it is defined in the class (and not inherited).
    If the attribute is not present or is inherited, an `AttributeError` is raised.

    >>> class A(object):
    ...     a = 1
    >>>
    >>> class B(A):
    ...     pass
    >>>
    >>> getownattr(A, 'a')
    1
    >>> getownattr(A, 'unknown')
    Traceback (most recent call last):
        ...
    AttributeError: type object 'A' has no attribute 'unknown'
    >>> getownattr(B, 'a')
    Traceback (most recent call last):
        ...
    AttributeError: type object 'B' has no directly defined attribute 'a'

    """
    attr = getattr(cls, attrib_name)

    for base_cls in cls.__mro__[1:]:
        a = getattr(base_cls, attrib_name, None)
        if attr is a:
            raise AttributeError("type object %r has no directly defined attribute %r" % (cls.__name__, attrib_name))

    return attr
