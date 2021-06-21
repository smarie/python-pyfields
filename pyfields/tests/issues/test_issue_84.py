import pytest

from pyfields import autofields, field, copy_value


@pytest.mark.parametrize("auto,deep", [(False, False), (False, True), (True, True)])
def test_issue_deepcopy_autofields(auto, deep):
    """Make sure that """

    class NotCopiable(object):
        def __deepcopy__(self, memodict={}):
            raise NotImplementedError()

        def __copy__(self):
            raise NotImplementedError()

    default_value = NotCopiable()

    with pytest.raises(ValueError) as exc_info:
        if auto:
            @autofields
            class Foo:
                a = default_value
        else:
            class Foo:
                a = field(default_factory=copy_value(default_value, deep=deep))

    extra = "deep-" if deep else ""
    assert str(exc_info.value).startswith("The provided default value %r can not be %scopied" % (default_value, extra))
