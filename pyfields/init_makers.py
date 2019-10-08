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
    use_type_hints = sys.version_info > (3, 0)
except ImportError:
    use_type_hints = False


from makefun import wraps, with_signature

from pyfields.core import collect_all_fields, PY36, USE_FACTORY, EMPTY, Field, pop_kwargs


def init_fields(*fields,   # type: Union[Field, Any]
                **kwargs
                ):
    """
    Decorator for an init method, so that fields are initialized before entering the method.

    By default, when the decorator is used without arguments or when `fields` is empty, all fields defined in the class
    are initialized. Fields inherited from parent classes are included, following the mro. The signature of the init
    method is modified so that it can receive values for these fields:

    >>> import sys, pytest
    >>> if sys.version_info < (3, 7): pytest.skip('doctest skipped')  # 3.6 help() is different on travis

    >>> from pyfields import field, init_fields
    >>> class Wall:
    ...     height: int = field(doc="Height of the wall in mm.")
    ...     color: str = field(default='white', doc="Color of the wall.")
    ...
    ...     @init_fields
    ...     def __init__(self, msg: str = 'hello'):
    ...         print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
    ...         self.non_field_attr = msg
    ...
    >>> help(Wall.__init__)
    Help on function __init__ in module pyfields.init_makers:
    <BLANKLINE>
    __init__(self, height: int, msg: str = 'hello', color: str = 'white')
        The `__init__` method generated for you when you use `@init_fields`
        or `make_init` with a non-None `post_init_fun` method.
    <BLANKLINE>
    >>> w = Wall(2)
    post init ! height=2, color=white, msg=hello


    The list of fields can be explicitly provided in `fields`.

    By default the init arguments will appear before the fields in the signature, wherever possible (mandatory args
    before mandatory fields, optional args before optional fields). You can change this behaviour by setting
    `init_args_before` to `False`.

    :param fields: list of fields to initialize before entering the decorated `__init__` method. For each of these
        fields a corresponding argument will be added in the method's signature. If an empty list is provided, all
        fields from the class will be used including inherited fields following the mro.
    :param init_args_before: If set to `True` (default), arguments from the decorated init method will appear before
        the fields when possible. If set to `False` the contrary will happen.
    :return:
    """
    init_args_before = pop_kwargs(kwargs, [('init_args_before', True)], allow_others=False)

    if len(fields) == 1:
        # used without argument ?
        f = fields[0]
        if isfunction(f) and not isinstance(f, Field) and init_args_before:
            # @init_fields decorator used without parenthesis

            # The list of fields is NOT explicit: we have no way to gather this list without creating a descriptor
            return InitDescriptor(user_init_fun=f, user_init_is_injected=False)

    def apply_decorator(init_fun):
        # @init_fields(...)

        # The list of fields is explicit AND names/type hints have been set already:
        # it is not easy to be sure of this (names yes, but annotations?) > prefer the descriptor anyway
        return InitDescriptor(fields=fields, user_init_fun=init_fun, user_init_args_before=init_args_before,
                              user_init_is_injected=False)

    return apply_decorator


def inject_fields(*fields  # type: Union[Field, Any]
                  ):
    """
    A decorator for `__init__` methods, to make them automatically expose arguments corresponding to all `*fields`.
    It can be used with or without arguments. If the list of fields is empty, it means "all fields from the class".

    The decorated `__init__` method should have an argument named `'fields'`. This argument will be injected with an
    object so that users can manually execute the fields initialization. This is done with `fields.init()`.

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6): pytest.skip('doctest skipped')

    >>> from pyfields import field, inject_fields
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

    :param fields: list of fields to initialize before entering the decorated `__init__` method. For each of these
        fields a corresponding argument will be added in the method's signature. If an empty list is provided, all
        fields from the class will be used including inherited fields following the mro.
    :return:
    """
    if len(fields) == 1:
        # used without argument ?
        f = fields[0]
        if isfunction(f) and not isinstance(f, Field):
            # @inject_fields decorator used without parenthesis

            # The list of fields is NOT explicit: we have no way to gather this list without creating a descriptor
            return InitDescriptor(user_init_fun=f, user_init_is_injected=True)

    def apply_decorator(init_fun):
        # @inject_fields(...)

        # The list of fields is explicit AND names/type hints have been set already:
        # it is not easy to be sure of this (names yes, but annotations?) > prefer the descriptor anyway
        return InitDescriptor(user_init_fun=init_fun, fields=fields, user_init_is_injected=True)

    return apply_decorator


def make_init(*fields,  # type: Union[Field, Any]
              **kwargs
              ):
    """
    Creates a constructor based on the provided fields.

    If `fields` is empty, all fields from the class will be used in order of appearance, then the ancestors (following
    the mro)

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6): pytest.skip('doctest skipped')

    >>> from pyfields import field, make_init
    ...
    >>> class Wall:
    ...     height = field(doc="Height of the wall in mm.")
    ...     color = field(default='white', doc="Color of the wall.")
    ...     __init__ = make_init()
    >>> w = Wall(1, color='blue')
    >>> assert vars(w) == {'color': 'blue', 'height': 1}

   If `fields` is not empty, only the listed fields will appear in the constructor and will be initialized upon init.

    >>> class Wall:
    ...     height = field(doc="Height of the wall in mm.")
    ...     color = field(default='white', doc="Color of the wall.")
    ...     __init__ = make_init(height)
    >>> w = Wall(1, color='blue')
    Traceback (most recent call last):
    ...
    TypeError: __init__() got an unexpected keyword argument 'color'

    `fields` can contain fields that do not belong to this class: typically they can be fields defined in a parent
    class. Note however that any field can be used, it is not mandatory to use class or inherited fields.

    >>> class Wall:
    ...     height: int = field(doc="Height of the wall in mm.")
    ...
    >>> class ColoredWall(Wall):
    ...     color: str = field(default='white', doc="Color of the wall.")
    ...     __init__ = make_init(Wall.__dict__['height'])
    ...
    >>> w = ColoredWall(1)
    >>> vars(w)
    {'height': 1}

    If a `post_init_fun` is provided, it should be a function with `self` as first argument. This function will be
    executed after all declared fields have been initialized. The signature of the resulting `__init__` function
    created will be constructed by blending all mandatory/optional fields with the mandatory/optional args in the
    `post_init_fun` signature. The ones from the `post_init_fun` will appear first except if `post_init_args_before`
    is set to `False`

    >>> class Wall:
    ...     height: int = field(doc="Height of the wall in mm.")
    ...     color: str = field(default='white', doc="Color of the wall.")
    ...
    ...     def post_init(self, msg='hello'):
    ...         print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
    ...         self.non_field_attr = msg
    ...
    ...     # only `height` and `foo` will be in the constructor
    ...     __init__ = make_init(height, post_init_fun=post_init)
    ...
    >>> w = Wall(1, 'hey')
    post init ! height=1, color=white, msg=hey
    >>> assert vars(w) == {'height': 1, 'color': 'white', 'non_field_attr': 'hey'}

    :param fields: the fields to include in the generated constructor signature. If no field is provided, all fields
        defined in the class will be included, as well as inherited ones following the mro.
    :param post_init_fun: (default: `None`) an optional function to call once all fields have been initialized. This
        function should have `self` as first argument. The rest of its signature will be blended with the fields in the
        generated constructor signature.
    :param post_init_args_before: boolean. Defines if the arguments from the `post_init_fun` should appear before
        (default: `True`) or after (`False`) the fields in the generated signature. Of course in all cases, mandatory
        arguments will appear after optional arguments, so as to ensure that the created signature is valid.
    :return: a constructor method to be used as `__init__`
    """
    # python <3.5 compliance: pop the kwargs following the varargs
    post_init_fun, post_init_args_before = pop_kwargs(kwargs, [('post_init_fun', None),
                                                               ('post_init_args_before', True)], allow_others=False)

    return InitDescriptor(fields=fields, user_init_fun=post_init_fun, user_init_args_before=post_init_args_before,
                          user_init_is_injected=False)


class InitDescriptor(object):
    """
    A class member descriptor for the `__init__` method that we create with `make_init`.
    The first time people access `cls.__init__`, the actual method will be created and injected in the class.
    This descriptor will then disappear and the class will behave normally.

    Inspired by https://stackoverflow.com/a/3412743/7262247
    """
    __slots__ = 'fields', 'user_init_is_injected', 'user_init_fun', 'user_init_args_before'

    def __init__(self, fields=None, user_init_is_injected=False, user_init_fun=None, user_init_args_before=True):
        self.fields = fields
        self.user_init_is_injected = user_init_is_injected
        self.user_init_fun = user_init_fun
        self.user_init_args_before = user_init_args_before

    # not useful and may slow things down anyway
    # def __set_name__(self, owner, name):
    #     if name != '__init__':
    #         raise ValueError("this should not happen")

    def __get__(self, obj, objtype):
        if objtype is not None:
            # <objtype>.__init__ has been accessed. Create the modified init
            fields = self.fields
            if fields is None or len(fields) == 0:
                # fields have not been access explicitly so they might have not been initialized yet.
                fields = collect_all_fields(objtype, auto_fix_fields=not PY36)
            elif not PY36:
                # take this opportunity to apply all field names including inherited
                # TODO set back inherited = False when the bug with class-level access is solved -> make_init will be ok then
                collect_all_fields(objtype, include_inherited=True, auto_fix_fields=True)

            # create the init method
            new_init = create_init(fields=fields, inject_fields=self.user_init_is_injected,
                                   user_init_fun=self.user_init_fun, user_init_args_before=self.user_init_args_before)

            # replace it forever in the class
            setattr(objtype, '__init__', new_init)

            # return the new init
            return new_init.__get__(obj, objtype)


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


def create_init(fields,                     # type: Iterable[Field]
                user_init_fun=None,         # type: Callable[[...], Any]
                inject_fields=False,        # type: bool
                user_init_args_before=True  # type: bool
                ):
    """
    Creates the new init function that will replace `init_fun`.

    :param fields:
    :param user_init_fun:
    :param inject_fields:
    :param user_init_args_before:
    :return:
    """
    # the list of parameters that should be exposed
    params = [Parameter('self', kind=Parameter.POSITIONAL_OR_KEYWORD)]

    if user_init_fun is None:
        # A - no function provided: expose a signature containing 'self' + fields
        field_names, _ = _insert_fields_at_position(fields, params, 1)
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
        # B - function provided - expose a signature containing 'self' + the function params + fields
        # start by inserting all fields
        field_names, _idx = _insert_fields_at_position(fields, params, 1)

        # then get the function signature
        user_init_sig = signature(user_init_fun)

        # Insert all parameters from the function except 'self'
        if user_init_args_before:
            mandatory_insert_idx, optional_insert_idx = 1, _idx
        else:
            mandatory_insert_idx, optional_insert_idx = _idx, len(params)

        fields_arg_found = False
        for p in islice(user_init_sig.parameters.values(), 1, None):  # remove the 'self' argument
            if inject_fields and p.name == 'fields':
                # injected argument
                fields_arg_found = True
                continue
            if p.default is p.empty:
                # mandatory
                params.insert(mandatory_insert_idx, p)
                mandatory_insert_idx += 1
                optional_insert_idx += 1
            else:
                # optional
                params.insert(optional_insert_idx, p)
                optional_insert_idx += 1

        if inject_fields and not fields_arg_found:
            # 'fields' argument not found in __init__ signature: impossible to inject, raise an error
            try:
                name = user_init_fun.__qualname__
            except AttributeError:
                name = user_init_fun.__name__
            raise ValueError("Error applying `@inject_fields` on `%s%s`: "
                             "no 'fields' argument is available in the signature." % (name, user_init_sig))

        # replace the signature with the newly created one
        new_sig = user_init_sig.replace(parameters=params)

        # and create the new init method
        if inject_fields:
            @wraps(user_init_fun, new_sig=new_sig)
            def __init__(self, *args, **kwargs):
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
                return user_init_fun(self, *args, **kwargs)

        else:
            @wraps(user_init_fun, new_sig=new_sig)
            def __init__(self, *args, **kwargs):
                """
                The `__init__` method generated for you when you use `@init_fields`
                or `make_init` with a non-None `post_init_fun` method.
                """
                # 1. self-assign all fields
                for field_name in field_names:
                    field_value = kwargs.pop(field_name)
                    if field_value is not USE_FACTORY:
                        # init the field with the provided value or the injected default value
                        setattr(self, field_name, field_value)
                    else:
                        # init the field with its factory, by just getting it
                        getattr(self, field_name)

                # 2. call your post-init method
                return user_init_fun(self, *args, **kwargs)

        return __init__


def _insert_fields_at_position(fields_to_insert,
                               params,
                               i,
                               field_names=None
                               ):
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
        annotation = _field.type_hint if _field.type_hint is not EMPTY else Parameter.empty

        # remember the list of field names for later use
        field_names.append(_field.name)

        # finally inject the new parameter in the signature
        new_param = Parameter(_field.name, kind=Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation)
        params.insert(where_to_insert, new_param)

    return field_names, last_mandatory_idx
