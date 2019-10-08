from typing import Union, Any, Callable, Iterable

from pyfields.core import Field


def init_fields(*fields: Union[Field, Any],
                init_args_before: bool = True
                ):
    ...


def inject_fields(*fields: Union[Field, Any],
                  ):
    ...


def make_init(*fields: Union[Field, Any],
              post_init_fun: Callable = None,
              post_init_args_before: bool = True
              ) -> Callable:
    ...


class InitDescriptor(object):
    def init(self, obj): ...
    ...


class InjectedInitFieldsArg(object):
    ...


def create_init(fields: Iterable[Field],
                user_init_fun: Callable[[...], Any] = None,
                inject_fields: bool = False,
                user_init_args_before: bool = True
                ):
    ...
