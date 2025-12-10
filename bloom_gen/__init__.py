try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("bloom")
    except PackageNotFoundError:
        __version__ = 'unset'
except ImportError:
    __version__ = 'unset'

# Library API exports
from bloom_gen.api import generate_debian, GenerateResult, copy_debian_to_dest

__all__ = ['generate_debian', 'GenerateResult', 'copy_debian_to_dest', '__version__']
