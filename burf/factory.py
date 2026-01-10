from typing import Union

from burf.scheme import StorageScheme
from burf.storage import GCS, HAS_GCS, HAS_S3, S3
from burf.storage.storage import Storage


class StorageFactory:
    """Factory for creating Storage instances based on scheme."""

    @staticmethod
    def create_storage(scheme: Union[str, StorageScheme]) -> Storage:
        """
        Creates a Storage instance for the given scheme.
        
        Args:
            scheme: 'gs', 's3' or StorageScheme enum
            
        Returns:
            Storage instance
            
        Raises:
            ImportError: If the dependencies for the requested scheme are not installed.
            ValueError: If the scheme is unknown.
        """
        if isinstance(scheme, str):
            try:
                scheme = StorageScheme(scheme)
            except ValueError:
                raise ValueError(f"Unknown storage scheme: {scheme}")

        if scheme == StorageScheme.S3:
            if not HAS_S3:
                raise ImportError(
                    "S3 dependencies not found. Please install them with: pip install burf[s3]"
                )
            return S3()
        
        elif scheme == StorageScheme.GCS:
            if not HAS_GCS:
                raise ImportError(
                    "GCS dependencies not found. Please install them with: pip install burf[gcs]"
                )
            return GCS()
            
        else:
            # Should be unreachable if Enum covers all cases
            raise ValueError(f"Unknown storage scheme: {scheme}")
