"""ukvocab is now uavocab.

This package was renamed `uavocab` at 0.5.0 to match uavocab.org. Installing
`ukvocab` installs `uavocab`, and this module re-exports it, so code written
against the old name keeps working:

    import uavocab            # the name to use
    import ukvocab            # still works, with a FutureWarning

https://pypi.org/project/uavocab/
"""

import sys
import warnings

import uavocab as _uavocab
from uavocab import *  # noqa: F401,F403  (the whole public API, by its __all__)
from uavocab import _store  # noqa: F401  (old code read ukvocab._store directly)

__all__ = list(_uavocab.__all__)

# `from ukvocab._store import manifest` keeps resolving too.
sys.modules.setdefault(__name__ + "._store", _store)

warnings.warn(
    "ukvocab has been renamed uavocab: `pip install uavocab` and `import uavocab`. "
    "The old name keeps working as an alias and will not be released again.",
    FutureWarning,
    stacklevel=2,
)


def __getattr__(name):
    # Anything else (including __version__, which uavocab resolves lazily)
    # comes from uavocab.
    return getattr(_uavocab, name)
