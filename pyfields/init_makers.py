#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys
from inspect import isfunction
from itertools import islice

try:
    from inspect import signature, Parameter, Signature
except ImportError:
    from funcsigs import signature, Parameter, Signature


try:  # python 3.5+
    from typing import Optional, Set, List, Callable, Dict, Type, Any, TypeVar, Union, Iterable, Tuple, Mapping
    from valid8.common_syntax import ValidationFuncs
    use_typing = sys.version_info > (3, 0)
except ImportError:
    use_type_hints = False


from makefun import wraps, with_signature

from pyfields.core import collect_all_fields, PY36, USE_FACTORY, EMPTY, Field


def inject_fields(*fields  # type: Field
                  ):
    """
    A decorator for `__init__` methods, to make them automatically expose arguments corresponding to all `*fields`.
    It can be used with or without arguments. If the list of fields is empty, it means "all fields from the class".

    The decorated `__init__` method should have an argument named `'fields'`. This argument will be injected with an
    object so that users can manually execute the fields initialization. This is done with `fields.init()`.

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6):
    ...     pytest.skip('doctest skipped')

    >>> from pyfields import field
    ...
    >>> class Wall(object):
    ...     height = field(doc="Height of the wall in mm.")
    ...     color = field(default='white', doc="Color of the wall.")
    ...
    ...     @inject_fields(height, color)
    ...     def __init__(self, fields):
    ...         # initialize all fields received
    ...         fields.init(self)
    ...
    ...     def __repr__(self):
    ...         return "Wall<height=%r, color=%r>" % (self.height, self.color)
    ...
    >>> Wall()
    Traceback (most recent call last):
    ...
    TypeError: __init__() missing 1 required positional argument: 'height'
    >>> Wall(1)
    Wall<height=1, color='white'>

    :param fields:
    :return:
    """
    if len(fields) == 1:
        init_fun_candidate = fields[0]
        if isfunction(init_fun_candidate):
            # called without arguments: return the modified init function
            return create_injected_init_possibly_with_descriptor(init_fun_candidate)

    # called with arguments: return a decorator
    return lambda init_fun: create_injected_init_possibly_with_descriptor(init_fun, fields)


class InjectedInitDescriptor(object):
    """
    A class member descriptor for the __init__ method that we create with `@inject_fields`.
    The first time people access `cls.__init__`, the actual method will be created and injected in the class.
    This descriptor will then disappear and the class will behave normally.

    Inspired by https://stackoverflow.com/a/3412743/7262247
    """
    __slots__ = 'init_fun', 'fields'

    def __init__(self, init_fun, fields=None):
        self.init_fun = init_fun
        # empty lists are reduced to None
        if fields is not None and len(fields) == 0:
            fields = None
        self.fields = fields

    # not useful and may slow things down anyway
    # def __set_name__(self, owner, name):
    #     if name != '__init__':
    #         raise ValueError("this should not happen")

    def __get__(self, obj, objtype):
        if objtype is not None:
            # <objtype>.__init__ has been accessed. Create the modified init
            fields = self.fields
            if fields is None:  # empty lists can not happen see constructor
                fields = collect_all_fields(objtype, auto_set_names=not PY36)
            elif not PY36:
                # take this opportunity to apply all field names
                collect_all_fields(objtype, include_inherited=False, auto_set_names=True)

            new_init = create_injected_init(self.init_fun, fields)

            # replace it forever in the class
            setattr(objtype, '__init__', new_init)

            # return the new init
            return new_init.__get__(obj, objtype)


create_injected_init_possibly_with_descriptor = InjectedInitDescriptor


# def _do_inject_fields(init_fun, fields=None):
#     """
#     A decorator for the `__init__` function
#
#     :param init_fun:
#     :return:
#     """
#     if fields is None or len(fields) == 0:
#         return InjectedInitDescriptor(init_fun)
#     else:
#         # explicit list of fields
#         # Note: we can not return it directly because the name might not be available yet ! TODO even in python 3.6?
#         # return create_injected_init(init_fun, fields)
#         return InjectedInitDescriptor(init_fun)


class InjectedInitFieldsArg(object):
    """
    The object that is injected in the users' `__init__` method as the `fields` argument,
    when it has been decorated with `@inject_fields`.

    All field values received from the generated `__init__` are available in `self.field_values`, and
    a `init()` method allows users to perform the initialization per se.
    """
    __slots__ = 'field_values'

    def __init__(self, **init_field_values):
        self.field_values = init_field_values

    def init(self, obj):
        """
        Initializes all fields on the provided object
        :param obj:
        :return:
        """
        for field_name, field_value in self.field_values.items():
            if field_value is not USE_FACTORY:
                # init the field with the provided value or the injected default value
                setattr(obj, field_name, field_value)
            else:
                # init the field with its factory
                getattr(obj, field_name)


def create_injected_init(init_fun,
                         fields  # type: Iterable[Field]
                         ):
    """
    Creates the new init function that will replace `init_fun`.

    :param init_fun:
    :param fields:
    :return:
    """
    # read the existing signature of __init__
    init_sig = signature(init_fun)
    params = list(init_sig.parameters.values())

    # find the index of the 'fields' parameter
    for i, p in enumerate(params):
        if p.name == 'fields':
            # found
            break
    else:
        # 'fields' not found: raise an error
        try:
            name = init_fun.__qualname__
        except AttributeError:
            name = init_fun.__name__
        raise ValueError("Error applying `@inject_fields` on `%s%s`: "
                         "no 'fields' argument is available in the signature." % (name, init_sig))

    # remove the fields parameter
    del params[i]

    # inject in the same position, all fields that should be included
    field_names, _ = _insert_fields_at_position(fields, params, i)

    # finally replace the signature with the newly created one
    new_sig = init_sig.replace(parameters=params)

    # and create the new init method
    @wraps(init_fun, new_sig=new_sig, func_name='__init__')
    def init_fun_mod(*args, **kwargs):
        """
        The `__init__` method generated for you when you use `@inject_fields` on your `__init__`
        """
        # 1. remove all field values received from the outer signature
        _fields = dict()
        for f_name in field_names:
            _fields[f_name] = kwargs.pop(f_name)

        # 2. inject our special variable
        kwargs['fields'] = InjectedInitFieldsArg(**_fields)

        # 3. call your __init__ method
        return init_fun(*args, **kwargs)

    return init_fun_mod


# --------- make_init

def make_init(*fields):
    """

    :param fields:
    :return:
    """
    # convert to list so that we can pop
    fields = list(fields)
    post_init_fun = None
    post_init_fun_idx = -1

    # find the init function in the list if any
    i = 0
    end = len(fields)
    while i < end:
        if isfunction(fields[i]):
            if post_init_fun is not None:
                raise ValueError("`make_init` only supports that you provide a single init function")

            # extract it from the list
            post_init_fun = fields.pop(i)
            post_init_fun_idx = i
            end -= 1
        else:
            i += 1

    if post_init_fun_idx == 0 and end == 0:
        post_init_fun_idx = -1
    return MadeInitDescriptor(fields, post_init_fun, post_init_fun_idx)


class MadeInitDescriptor(object):
    """
    A class member descriptor for the __init__ method that we create with `make_init`.
    The first time people access `cls.__init__`, the actual method will be created and injected in the class.
    This descriptor will then disappear and the class will behave normally.

    Inspired by https://stackoverflow.com/a/3412743/7262247
    """
    __slots__ = 'fields', 'post_init_fun', 'post_init_fun_idx'

    def __init__(self, fields, post_init_fun=None, post_init_fun_idx=-1):
        self.fields = fields
        self.post_init_fun = post_init_fun
        self.post_init_fun_idx = post_init_fun_idx

    # not useful and may slow things down anyway
    # def __set_name__(self, owner, name):
    #     if name != '__init__':
    #         raise ValueError("this should not happen")

    def __get__(self, obj, objtype):
        if objtype is not None:
            # <objtype>.__init__ has been accessed. Create the modified init
            fields = self.fields
            if fields is None or len(fields) == 0:
                fields = collect_all_fields(objtype, auto_set_names=not PY36)
            elif not PY36:
                # take this opportunity to apply all field names
                collect_all_fields(objtype, include_inherited=False, auto_set_names=True)

            new_init = create_init(fields, self.post_init_fun, self.post_init_fun_idx)

            # replace it forever in the class
            setattr(objtype, '__init__', new_init)

            # return the new init
            return new_init.__get__(obj, objtype)


def create_init(fields,               # type: Iterable[Field]
                post_init_fun=None,   # type: Callable[[...], Any]
                post_init_fun_idx=-1  # type: int
                ):
    """
    Creates the new init function that will replace `init_fun`.

    :param fields:
    :param post_init_fun:
    :param post_init_fun_idx:
    :return:
    """
    params = [Parameter('self', kind=Parameter.POSITIONAL_OR_KEYWORD)]

    if post_init_fun is None:
        # A/ no function provided
        assert post_init_fun_idx < 0
        field_names, _ = _insert_fields_at_position(fields, params, 1)

        # create the signature to expose
        new_sig = Signature(parameters=params)

        # and create the new init method
        @with_signature(new_sig, func_name='__init__')
        def init_fun(*args, **kwargs):
            """
            The `__init__` method generated for you when you use `make_init`
            """
            # 1. get 'self'
            try:
                # most of the time 'self' will be received like that
                self = kwargs['self']
            except IndexError:
                self = args[0]

            # 2. self-assign all fields
            for field_name in field_names:
                field_value = kwargs[field_name]
                if field_value is not USE_FACTORY:
                    # init the field with the provided value or the injected default value
                    setattr(self, field_name, field_value)
                else:
                    # init the field with its factory, by just getting it
                    getattr(self, field_name)

        return init_fun

    else:
        # B/ function provided - extract its signature
        post_init_sig = signature(post_init_fun)

        if post_init_fun_idx >= 0:
            # First take all fields that should appear BEFORE the init function signature
            field_names, _ = _insert_fields_at_position(fields[:post_init_fun_idx], params, 1)

            # Insert all parameters from the postinit fun except 'self'
            params += islice(post_init_sig.parameters.values(), 1, None)  # remove the 'self' argument

            # Then all the remaining fields
            _insert_fields_at_position(fields[post_init_fun_idx:], params, len(params), field_names)
        else:
            # "intelligent mix"
            field_names, optional_insert_idx = _insert_fields_at_position(fields, params, 1)
            mandatory_insert_idx = 1

            # Insert all parameters from the postinit fun except 'self'
            for p in islice(post_init_sig.parameters.values(), 1, None):  # remove the 'self' argument
                if p.default is p.empty:
                    # mandatory
                    params.insert(mandatory_insert_idx, p)
                    mandatory_insert_idx += 1
                else:
                    # optional
                    params.insert(optional_insert_idx, p)
                    optional_insert_idx += 1

        # replace the signature with the newly created one
        new_sig = post_init_sig.replace(parameters=params)

        # and create the new init method
        @wraps(post_init_fun, new_sig=new_sig, func_name='__init__')
        def init_fun_mod(*args, **kwargs):
            """
            The `__init__` method generated for you when you use `make_init` with a `post_init_fun` method in the args
            """
            # 1. get 'self'
            try:
                # most of the time 'self' will be received like that
                self = kwargs['self']
            except IndexError:
                self = args[0]

            # 2. self-assign all fields
            for field_name in field_names:
                field_value = kwargs.pop(field_name)
                if field_value is not USE_FACTORY:
                    # init the field with the provided value or the injected default value
                    setattr(self, field_name, field_value)
                else:
                    # init the field with its factory, by just getting it
                    getattr(self, field_name)

            # 3. call your post-init method
            return post_init_fun(*args, **kwargs)

        return init_fun_mod


def _insert_fields_at_position(fields_to_insert, params, i, field_names=None):
    """
    Note: preserve order as much as possible, but automatically place all mandatory fields first so that the
    signature is valid.

    :param fields_to_insert:
    :param field_names:
    :param i:
    :param params:
    :return:
    """
    if field_names is None:
        field_names = []

    last_mandatory_idx = i
    for _field in reversed(fields_to_insert):
        # Is this field optional ?
        if _field.is_mandatory:
            # mandatory
            where_to_insert = i
            last_mandatory_idx += 1
            default = Parameter.empty
        elif _field.is_default_factory:
            # optional with a default value factory: place a specific symbol in the signature to indicate it
            default = USE_FACTORY
            where_to_insert = last_mandatory_idx
        else:
            # optional with a default value
            default = _field.default
            where_to_insert = last_mandatory_idx

        # Are there annotations on the field ?
        annotation = _field.annotation if _field.annotation is not EMPTY else Parameter.empty

        # remember the list of field names for later use
        field_names.append(_field.name)

        # finally inject the new parameter in the signature
        new_param = Parameter(_field.name, kind=Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation)
        params.insert(where_to_insert, new_param)

    return field_names, last_mandatory_idx
