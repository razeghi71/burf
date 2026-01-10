import sys
from typing import Optional

from burf.storage import GCS, HAS_GCS, HAS_S3, S3
from burf.storage.storage import Storage


class StorageFactory:
    """Factory for creating Storage instances based on scheme."""

    @staticmethod
    def create_storage(scheme: str, project_or_profile: Optional[str] = None) -> Storage:
        """
        Creates a Storage instance for the given scheme.
        
        Args:
            scheme: 'gs' or 's3'
            project_or_profile: Optional project ID (for GCS) or profile name (for S3)
            
        Returns:
            Storage instance
            
        Raises:
            ImportError: If the dependencies for the requested scheme are not installed.
            ValueError: If the scheme is unknown.
        """
        if scheme == "s3":
            if not HAS_S3:
                raise ImportError(
                    "S3 dependencies not found. Please install them with: pip install burf[s3]"
                )
            return S3(profile=project_or_profile)
        
        elif scheme == "gs":
            if not HAS_GCS:
                raise ImportError(
                    "GCS dependencies not found. Please install them with: pip install burf[gcs]"
                )
            return GCS(project=project_or_profile)
            
        else:
            raise ValueError(f"Unknown storage scheme: {scheme}")
