from burf.storage.storage import Storage

try:
    from burf.storage.gcs import GCS
    HAS_GCS = True
except ImportError:
    GCS = None
    HAS_GCS = False

try:
    from burf.storage.s3 import S3
    HAS_S3 = True
except ImportError:
    S3 = None
    HAS_S3 = False

__all__ = ["Storage", "GCS", "S3", "HAS_GCS", "HAS_S3"]
