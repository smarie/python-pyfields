# Authors: Sylvain MARIE <sylvain.marie@se.com>
#          + All contributors to <https://github.com/smarie/python-pyfields>
#
# License: 3-clause BSD, <https://github.com/smarie/python-pyfields/blob/master/LICENSE>
import sys

from pkg_resources import get_distribution


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
        except BaseException:
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
    from packaging.version import parse as parse_version
    try:
        from typeguard import check_type as ct

        # Note: only do this when we are sure that typeguard can be imported, otherwise this is slow
        # see https://github.com/smarie/python-getversion/blob/ee495acf6cf06c5e860713edeee396206368e458/getversion/main.py#L84
        typeguard_version = get_distribution("typeguard").version
        if parse_version(typeguard_version) < parse_version("3.0.0"):
            check_type = ct
        else:
            # Name has disappeared from 3.0.0
            def check_type(name, value, typ):
                ct(value, typ)

        try:
            from typing import Union
        except ImportError:
            # (a) typing is not available, transform iterables of types into several calls
            def assert_is_of_type(field, value, typ):
                """
                Type checker relying on `typeguard` (python 3.5+)

                :param field:
                :param value:
                :param typ:
                :return:
                """
                try:
                    # iterate on the types
                    t_gen = (t for t in typ)
                except TypeError:
                    # not iterable : a single type
                    try:
                        check_type(field.qualname, value, typ)
                    except Exception as e:
                        # raise from
                        new_e = FieldTypeError(field, value, typ)
                        new_e.__cause__ = e
                        raise new_e
                else:
                    # iterate and try them all
                    e = None
                    for _t in t_gen:
                        try:
                            check_type(field.qualname, value, typ)
                            return  # success !!!!
                        except Exception as e1:
                            e = e1  # failed: lets try another one

                    # raise from
                    if e is not None:
                        new_e = FieldTypeError(field, value, typ)
                        new_e.__cause__ = e
                        raise new_e

        else:
            # (b) typing is available, use a Union
            def assert_is_of_type(field, value, typ):
                """
                Type checker relying on `typeguard` (python 3.5+)

                :param field:
                :param value:
                :param typ:
                :return:
                """
                try:
                    check_type(field.qualname, value, Union[typ])
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
            # from valid8.utils.typing_inspect import is_typevar, is_union_type, get_args
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
                try:
                    is_ok = isinstance(value, types)
                except TypeError as e:
                    if e.args[0].startswith("Subscripted generics cannot"):
                        raise TypeError("Neither typeguard not pytypes is installed - therefore it is not possible to "
                                        "validate subscripted typing structures such as %s" % types)
                    else:
                        raise
                else:
                    if not is_ok:
                        raise FieldTypeError(field, value, typ)

    return assert_is_of_type


try:  # very minimal way to check if typing it available, for runtime type checking
    # noinspection PyUnresolvedReferences
    from typing import Tuple  # noqa
except ImportError:
    assert_is_of_type = None
else:
    assert_is_of_type = _make_assert_is_of_type()


PY36 = sys.version_info >= (3, 6)
get_type_hints = None
if PY36:
    try:
        from typing import get_type_hints as gth

        def get_type_hints(obj, globalns=None, localns=None):
            """
            Fixed version of typing.get_type_hints to handle self forward references
            """
            if globalns is None and localns is None and isinstance(obj, type):
                localns = {obj.__name__: obj}
            return gth(obj, globalns=globalns, localns=localns)

    except ImportError:
        pass
