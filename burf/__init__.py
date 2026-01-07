__all__ = ["__version__"]

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("burf")
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed (e.g. running from a source checkout).
    __version__ = "0.0.0"

