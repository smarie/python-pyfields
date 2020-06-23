#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2020. All right reserved.
try:
    from inspect import signature
except ImportError:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from funcsigs import signature

from makefun import wraps


def duckcheck(f):
    """
    A decorator for functions. It adds "duck-checking" for their annotated arguments
    :return:
    """
    s = signature(f)
    params = s.parameters
    return_hint = s.return_annotation

    @wraps(f)
    def func_wrapper(*args, **kwargs):
        bound = s.bind(*args, **kwargs)
        # check the args
        for name, received_arg in bound.arguments():
            p_def = params[name]
            if p_def.annotation is not p_def.empty:
                p_def.annotation

        # execute the function
        res = f(*args, **kwargs)

        # check the result


        # return it
        return res

    return func_wrapper
