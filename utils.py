"""
Utility functions for GMS importer
"""

import mathutils
import logging
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("GMS_Importer")


def log_info(message):
    """Log info message"""
    print(f"[GMS] {message}")
    logger.info(message)


def log_warning(message):
    """Log warning message"""
    print(f"[GMS WARNING] {message}")
    logger.warning(message)


def log_error(message):
    """Log error message"""
    print(f"[GMS ERROR] {message}")
    logger.error(message)


def log_debug(message):
    """Log debug message"""
    print(f"[GMS DEBUG] {message}")
    logger.debug(message)


def convert_coordinate_system(vector, system='BLENDER'):
    """
    Convert coordinates from PSP system to Blender system
    
    PSP: Y-up, right-handed
    Blender: Z-up, right-handed
    
    FIXED: Conversion: (X, Y, Z) PSP -> (X, Z, -Y) Blender
    This properly converts Y-up to Z-up without inverting the model
    """
    if system == 'BLENDER':
        # PSP (X, Y, Z) -> Blender (X, Z, -Y)
        # Y becomes Z (up axis)
        # Z becomes -Y (forward/back axis, negated to maintain handedness)
        return mathutils.Vector((vector[0], vector[2], -vector[1]))
    else:
        # Keep original
        return mathutils.Vector((vector[0], vector[1], vector[2]))


def convert_rotation(rotation, system='BLENDER'):
    """
    Convert rotation from PSP to Blender
    
    Args:
        rotation: Vector3 of Euler angles in radians (ZYX order)
        system: 'BLENDER' or 'PSP'
    """
    if system == 'BLENDER':
        # PSP uses ZYX Euler order, Blender uses XYZ
        # Convert from PSP (Z, Y, X) to Blender (X, Y, Z)
        euler = mathutils.Euler((rotation.x, rotation.y, rotation.z), 'ZYX')
        # Convert to quaternion
        quat = euler.to_quaternion()
        
        # Apply coordinate system transform to match mesh conversion
        # Rotate around X axis to convert Y-up to Z-up
        correction = mathutils.Euler((1.5708, 0, 0), 'XYZ')  # 90 degrees in radians
        quat = correction.to_quaternion() @ quat
        
        return quat.to_euler('XYZ')
    else:
        return mathutils.Euler((rotation.x, rotation.y, rotation.z), 'ZYX')


def convert_quaternion(quat, system='BLENDER'):
    """
    Convert quaternion from PSP to Blender
    
    Args:
        quat: Vector4 (x, y, z, w)
        system: 'BLENDER' or 'PSP'
    """
    if system == 'BLENDER':
        # PSP quaternion: (x, y, z, w)
        q = mathutils.Quaternion((quat.w, quat.x, quat.y, quat.z))
        
        # Apply coordinate system transform
        correction = mathutils.Euler((1.5708, 0, 0), 'XYZ').to_quaternion()
        q = correction @ q
        
        return q
    else:
        return mathutils.Quaternion((quat.w, quat.x, quat.y, quat.z))


def apply_scale(vector, scale):
    """Apply scale factor to vector"""
    return mathutils.Vector((vector[0] * scale, vector[1] * scale, vector[2] * scale))


def sanitize_name(name):
    """Sanitize name for Blender"""
    # Replace invalid characters
    name = name.replace('\\', '_').replace('/', '_')
    name = name.replace(':', '_').replace('*', '_')
    name = name.replace('?', '_').replace('"', '_')
    name = name.replace('<', '_').replace('>', '_')
    name = name.replace('|', '_')
    return name


def get_texture_path_variants(base_path, texture_name):
    """
    Get possible texture file paths
    
    FIXED: Returns list of paths to try with TM2, PNG, and DDS extensions
    """
    base_dir = os.path.dirname(base_path)
    variants = []
    
    # Remove any existing extension from texture_name
    texture_basename = os.path.splitext(texture_name)[0]
    
    # Try different extensions in order of preference
    extensions = ['.tm2', '.TM2', '.png', '.PNG', '.dds', '.DDS', '.jpg', '.JPG', '.jpeg', '.JPEG']
    
    for ext in extensions:
        # Try in the same directory as GMS file
        path = os.path.join(base_dir, texture_basename + ext)
        variants.append(path)
        
        # Try in a texture subdirectory
        texture_dir = os.path.join(base_dir, 'texture')
        if os.path.exists(texture_dir):
            path = os.path.join(texture_dir, texture_basename + ext)
            variants.append(path)
        
        # Try in a textures subdirectory
        textures_dir = os.path.join(base_dir, 'textures')
        if os.path.exists(textures_dir):
            path = os.path.join(textures_dir, texture_basename + ext)
            variants.append(path)
        
        # Try one level up in texture folder
        parent_dir = os.path.dirname(base_dir)
        texture_dir_up = os.path.join(parent_dir, 'texture')
        if os.path.exists(texture_dir_up):
            path = os.path.join(texture_dir_up, texture_basename + ext)
            variants.append(path)
    
    return variants


def find_texture_file(base_path, texture_name):
    """
    FIXED: Find texture file, checking multiple possible locations and extensions
    Supports TM2, PNG, DDS, and other common formats
    """
    log_debug(f"Searching for texture: {texture_name}")
    
    variants = get_texture_path_variants(base_path, texture_name)
    
    for path in variants:
        if os.path.exists(path):
            log_info(f"Found texture: {path}")
            return path
    
    log_warning(f"Texture not found: {texture_name} (searched {len(variants)} locations)")
    return None