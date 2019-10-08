# Why `pyfields` ?

During the few years I spent exploring the python world, I tried several times to find a "good" way to create classes where fields could be 

 - declared explicitly in a compact way
 - with optional validation and conversion
 - with as little call overhead as possible
 - without messing with the `__init__` and `__setattr__` methods

I discovered:
 
 - [`@property`](https://docs.python.org/3/library/functions.html#property), that is a good start but adds a python call cost on access and lacks the possibility to add validation and conversion in a compact declaration. It relies on the generic python [descriptors](https://docs.python.org/3/howto/descriptor.html) mechanism.
 
 - [`attrs`](http://www.attrs.org/), a great way to define classes with many out-of-the-box features (representation, hashing, constructor, ...). Its philosophy is that objects should be immutable (They *can* be mutable, actually they are by default, but [the validators are not executed on value modification](https://github.com/python-attrs/attrs/issues/160#issuecomment-284726744) as of 0.19). The way it works is by creating a "smart"  `__init__` script that contains all the logic (see [here](https://github.com/python-attrs/attrs/blob/22b8cb1c4cdb155dea0ca01648f94804b7b3fbfc/src/attr/_make.py#L1392)), and possibly a `__setattr__` if you ask for immutable objects with `frozen=True`.

 - [`autoclass`](https://smarie.github.io/python-autoclass/) was one of my first open-source projects in python: I tried to create a less optimized version of `attrs`, but at least something that would support basic use cases. The main difference with `attrs` is that fields are defined using the `__init__` signature, instead of class attributes, and it is possible to define custom setters to perform validation, that are effectively called on value modification. I also developed at the time a validation lib [`valid8`](https://smarie.github.io/python-valid8/)) that works with `autoclass` and `attrs`. The result has been used in industrial projects. But it is still not satisfying because relying on the `__init__` signature to define the fields is not very elegant and flexible in particular in case of multiple inheritance.
 
 - [PEP557 `dataclasses`](https://docs.python.org/3/library/dataclasses.html) was largely inspired by and is roughly equivalent to `attrs`, although a few design choices differ and its scope seems more limited.
 
This topic was left aside for a moment, until half 2019 where I thought that I had accumulated enough python expertise (with [`makefun`](https://smarie.github.io/python-makefun/), [`decopatch`](https://smarie.github.io/python-decopatch/) and [many pytest libraries](https://github.com/smarie/ALL_OF_THE_ABOVE#python)) to have a fresh look on it. In the meantime I had discovered:

 - [`traitlets`](https://traitlets.readthedocs.io/en/stable/) which provides a quite elegant way to define typed fields and define validation, but requires the classes to inherit from `HasTraits`, and does not allow users to define converters.
 
 - [`traits`](https://docs.enthought.com/traits/)
 
  - werkzeug's [`@cached_property`](https://werkzeug.palletsprojects.com/en/0.15.x/utils/#werkzeug.utils.cached_property) and sagemath's [`@lazy_attribute`](http://doc.sagemath.org/html/en/reference/misc/sage/misc/lazy_attribute.html), that both rely on the descriptor protocol to define class fields, but lack compacity
 
 - [`pydantic`](https://pydantic-docs.helpmanual.io/) embraces python 3.6+ type hints (that can be defined on class attributes). It is quite elegant, is compliant with `dataclasses`, and supports validators that can act on single or multiple fields. It requires classes to inherit from a `BaseModel`. It does not seem to support converters as of version 0.32, rather, some type conversion happens behind the scenes (see for example [this issue](https://github.com/samuelcolvin/pydantic/issues/453)). But it looks definitely promising.
 
I was still not satisfied by the landscape. So I wrote this alternative, maybe it can fit in *some* use cases ! Do not hesitate to provide feedback in the issues page.
