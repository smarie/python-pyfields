from typing import Union, Any, Callable, Iterable

from pyfields.core import Field


def inject_fields(*fields: Union[Field, Any],
                  ):
    ...


class InjectedInitDescriptor(object):
    ...


class InjectedInitFieldsArg(object):
    ...


def create_injected_init(init_fun,
                         fields: Iterable[Field]
                         ):
    ...


def init_fields(*fields: Union[Field, Any],
                init_args_before: bool = True
                ):
    ...


def make_init(*fields: Union[Field, Any],
              post_init_fun: Callable = None,
              post_init_args_before: bool = True
              ):
    ...
