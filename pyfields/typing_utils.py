#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.


class FieldTypeError(TypeError):  # FieldError
    """
    Error raised when the type of a field does not match expected type(s).
    """
    __slots__ = ('field', 'value', 'expected_types')

    def __init__(self, field, value, expected_types):
        self.field = field
        self.value = value
        # noinspection PyBroadException
        try:
            if len(expected_types) == 1:
                expected_types = expected_types[0]
        except:
            pass
        self.expected_types = expected_types

    def __str__(self):
        # representing the object might fail, protect ourselves
        # noinspection PyBroadException
        try:
            val_repr = repr(self.value)
        except Exception as e:
            val_repr = "<error while trying to represent value: %s>" % e

        # detail error message
        # noinspection PyBroadException
        try:
            # tuple or iterable of types ?
            sub_msg = "Value type should be one of (%s)" % ', '.join(("%s" % _t for _t in self.expected_types))
        except:  # noqa E722
            # single type
            sub_msg = "Value should be of type %s" % (self.expected_types,)

        return "Invalid value type provided for '%s'. %s. Instead, received a '%s': %s"\
               % (self.field.qualname, sub_msg, self.value.__class__.__name__, val_repr)


def _make_assert_is_of_type():
    try:
        from typeguard import check_type

        def assert_is_of_type(field, value, typ):
            """
            Type checker relying on `typeguard` (python 3.5+)

            :param field:
            :param value:
            :param typ:
            :return:
            """
            try:
                check_type(field.qualname, value, typ)
            except Exception as e:
                # raise from
                new_e = FieldTypeError(field, value, typ)
                new_e.__cause__ = e
                raise new_e

    except ImportError:
        try:
            from pytypes import is_of_type

            def assert_is_of_type(field, value, typ):
                """
                Type checker relying on `pytypes` (python 2+)

                :param field:
                :param value:
                :param typ:
                :return:
                """
                try:
                    valid = is_of_type(value, typ)
                except Exception as e:
                    # raise from
                    new_e = FieldTypeError(field, value, typ)
                    new_e.__cause__ = e
                    raise new_e
                else:
                    if not valid:
                        raise FieldTypeError(field, value, typ)

        except ImportError:
            from valid8.utils.typing_inspect import is_typevar, is_union_type, get_args
            from valid8.utils.typing_tools import resolve_union_and_typevar

            def assert_is_of_type(field, value, typ):
                """
                Neither `typeguard` nor `pytypes` are available on this platform.

                This is a "light" implementation that basically resolves all `Union` and `TypeVar` into a flat list and
                then calls `isinstance`.

                :param field:
                :param value:
                :param typ:
                :return:
                """
                types = resolve_union_and_typevar(typ)
                if not isinstance(value, types):
                    raise FieldTypeError(field, value, typ)

    return assert_is_of_type


try:  # very minimal way to check if typing it available, for runtime type checking
    # noinspection PyUnresolvedReferences
    from typing import Tuple
    assert_is_of_type = _make_assert_is_of_type()
except ImportError:
    assert_is_of_type = None
