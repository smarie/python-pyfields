#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.


try:
    # typeguard available ? (python 3.5+)
    from typeguard import checktype as assert_is_of_type

except ImportError:
    try:
        # pytypes available ? (python 2+)
        from pytypes import is_of_type

        def assert_is_of_type(name, value, typ):
            if not is_of_type(value, typ):
                # representing the object might fail, protect ourselves
                # noinspection PyBroadException
                try:
                    val_repr = repr(value)
                except Exception as e:
                    val_repr = "<error while trying to represent object: %s>" % e

                # detail error message
                submsg = "Value should be of type %s" % (typ, )

                raise TypeError("Invalid value type provided for '%s'. %s. Instead, received a '%s': %s"
                                % (name, submsg, value.__class__.__name__, val_repr))

    except ImportError:
        # neither typeguard nor pytypes are available. Best effort...

        from valid8.utils.typing_inspect import is_typevar, is_union_type, get_args
        from valid8.utils.typing_tools import resolve_union_and_typevar

        def assert_is_of_type(name, value, typ):
            types = resolve_union_and_typevar(typ)
            if not isinstance(value, types):
                # representing the object might fail, protect ourselves
                # noinspection PyBroadException
                try:
                    val_repr = repr(value)
                except Exception as e:
                    val_repr = "<error while trying to represent object: %s>" % e

                # detail error message
                submsg = "Value should be of type %s" % (typ, )

                raise TypeError("Invalid value type provided for '%s'. %s. Instead, received a '%s': %s"
                                % (name, submsg, value.__class__.__name__, val_repr))
