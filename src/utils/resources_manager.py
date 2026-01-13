"""
Resource manager for handling portable file references.
Copies external files to resources folder and manages relative paths.
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from typing import Optional


def get_resources_base_path() -> Path:
    """Get the base path for resources folder (next to viewer_config.json)."""
    # Handle PyInstaller bundled executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # _MEIPASS is the temp folder PyInstaller uses, sys.executable is the exe location
        if hasattr(sys, '_MEIPASS'):
            # During extraction, use the temp folder
            base_path = Path(sys.executable).parent
        else:
            # After extraction, use the exe directory
            base_path = Path(sys.executable).parent
    else:
        # Running as script
        current_file = Path(__file__)
        # Go up from src/utils/resources_manager.py to project root
        base_path = current_file.parent.parent.parent
    
    return base_path / "resources"


def get_resources_images_path() -> Path:
    """Get the path to resources/images folder."""
    return get_resources_base_path() / "images"


def get_resources_projects_path() -> Path:
    """Get the path to resources/projects folder."""
    return get_resources_base_path() / "projects"


def ensure_resources_directories():
    """Ensure resources directories exist."""
    get_resources_images_path().mkdir(parents=True, exist_ok=True)
    get_resources_projects_path().mkdir(parents=True, exist_ok=True)


def copy_image_to_resources(source_path: str) -> str:
    """
    Copy an image file to resources/images/ and return relative path.
    
    Args:
        source_path: Absolute path to source image file
        
    Returns:
        Relative path from resources folder (e.g., "images/filename.jpg")
    """
    if not source_path or not os.path.exists(source_path):
        return ""
    
    ensure_resources_directories()
    
    source = Path(source_path)
    # Generate a unique filename to avoid conflicts
    # Use hash of original path + filename to ensure uniqueness
    name_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
    file_ext = source.suffix
    new_filename = f"{source.stem}_{name_hash}{file_ext}"
    
    dest_path = get_resources_images_path() / new_filename
    
    # Copy the file
    shutil.copy2(source_path, dest_path)
    
    # Return relative path from resources folder
    return f"images/{new_filename}"


def copy_project_to_resources(source_path: str) -> str:
    """
    Copy a project file to resources/projects/ and return relative path.
    
    Args:
        source_path: Absolute path to source project file
        
    Returns:
        Relative path from resources folder (e.g., "projects/filename.json")
    """
    if not source_path or not os.path.exists(source_path):
        return ""
    
    ensure_resources_directories()
    
    source = Path(source_path)
    # Generate a unique filename to avoid conflicts
    name_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
    file_ext = source.suffix
    new_filename = f"{source.stem}_{name_hash}{file_ext}"
    
    dest_path = get_resources_projects_path() / new_filename
    
    # Copy the file
    shutil.copy2(source_path, dest_path)
    
    # Return relative path from resources folder
    return f"projects/{new_filename}"


def resolve_resource_path(relative_path: str) -> Optional[str]:
    """
    Resolve a relative resource path to absolute path.
    
    Args:
        relative_path: Relative path from resources folder (e.g., "images/photo.jpg")
        
    Returns:
        Absolute path to the resource file, or None if not found
    """
    if not relative_path:
        return None
    
    # Handle both old absolute paths and new relative paths
    if os.path.isabs(relative_path):
        # Old absolute path - check if it exists
        if os.path.exists(relative_path):
            return relative_path
        return None
    
    # New relative path from resources folder
    resource_path = get_resources_base_path() / relative_path
    if resource_path.exists():
        return str(resource_path)
    
    return None


def migrate_absolute_path_to_relative(absolute_path: str, resource_type: str = "image") -> str:
    """
    Migrate an absolute path to a relative path by copying to resources.
    
    Args:
        absolute_path: Absolute path to migrate
        resource_type: "image" or "project"
        
    Returns:
        Relative path from resources folder
    """
    if not absolute_path or not os.path.exists(absolute_path):
        return ""
    
    if resource_type == "image":
        return copy_image_to_resources(absolute_path)
    elif resource_type == "project":
        return copy_project_to_resources(absolute_path)
    else:
        return ""
