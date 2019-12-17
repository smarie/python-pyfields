#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys

from pyfields import Field, field, make_init, copy_value


PY36 = sys.version_info >= (3, 6)


def autofields(check_types=True,
               include_upper=False,
               include_dunder=False):
    """

    :param cls:
    :return:
    """
    def _autofields(cls):
        NO_DEFAULT = object()

        try:
            # Are type hints present ?
            cls_annotations = cls.__annotations__
        except AttributeError:
            # No type hints: shortcut
            members_defs = ((k, None, v) for k, v in cls.__dict__.items())
        else:
            # Fill the list of potential fields definitions
            members_defs = []
            cls_dict = cls.__dict__

            if not PY36:
                # TODO is this even possible ? does not seem so
                # dont care about the order, it is not preserved
                # -- fields with type hint
                for member_name, type_hint in cls_annotations.items():
                    members_defs.append((member_name, type_hint, cls_dict.get(member_name, NO_DEFAULT)))

                # -- fields without type hint
                members_with_type = set(cls_annotations.keys())
                for member_name, default_value in cls_dict.items():
                    if member_name not in members_with_type:
                        members_defs.append((member_name, None, default_value))

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

        for member_name, type_hint, default_value in members_defs:
            # Main loop : for each
            if not include_upper and member_name == member_name.upper():
                continue
            elif (include_dunder and is_reserved_dunder(member_name)) \
                    or is_dunder(member_name):
                continue
            elif callable(default_value) or isinstance(default_value, Field):
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

                # Attach the newly created field to the class
                setattr(cls, member_name, new_field)
                new_field.set_as_cls_member(cls, member_name, type_hint=type_hint)

        # Finally, make init if not present
        if '__init__' not in cls.__dict__:
            new_init = make_init()
            cls.__init__ = new_init
            new_init.__set_name__(cls, '__init__')

        return cls

    if check_types is not True and check_types is not False and isinstance(check_types, type):
        # called without arguments @autofields: check_types is the decorated class
        assert include_upper is False
        assert include_dunder is False
        return _autofields(cls=check_types)
    else:
        # called with arguments @autofields(...): return the decorator
        return _autofields


def is_dunder(name):
    return len(name) >= 4 and name.startswith('__') and name.endswith('__')


def is_reserved_dunder(name):
    return name in ('__doc__', '__name__', '__qualname__', '__module__', '__code__', '__globals__',
                    '__dict__', '__closure__', '__annotations__')  # '__defaults__', '__kwdefaults__')
