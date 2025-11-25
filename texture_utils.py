"""
Texture utilities for GMS importer - FULLY FIXED VERSION
FIXED: Handles TM2 conversion and texture loading with PNG/DDS fallbacks
"""

import os
import subprocess
import bpy
from . import utils


def convert_tm2_to_png(tm2_path, output_path=None):
    """
    Convert TM2 file to PNG using gimconv
    
    Args:
        tm2_path: Path to TM2 file
        output_path: Output PNG path (optional, defaults to same name with .png)
    
    Returns:
        Path to PNG file if successful, None otherwise
    """
    if not os.path.exists(tm2_path):
        utils.log_error(f"TM2 file not found: {tm2_path}")
        return None
    
    # Get gimconv path
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(addon_dir, 'tools', 'gim', 'gimconv')
    
    # Try different gimconv executable names
    gimconv_names = [
        'gimconv.exe',  # Windows
        'gimconv',      # Linux/Mac
        'GimConv.exe',  # Alternative
    ]
    
    gimconv_path = None
    for name in gimconv_names:
        test_path = os.path.join(tools_dir, name)
        if os.path.exists(test_path):
            gimconv_path = test_path
            break
    
    if not gimconv_path:
        utils.log_warning(f"gimconv not found in {tools_dir}, skipping TM2 conversion")
        utils.log_warning("Place gimconv executable in: gms_importer/tools/gim/gimconv/")
        return None
    
    # Determine output path
    if output_path is None:
        output_path = os.path.splitext(tm2_path)[0] + '.png'
    
    # Convert TM2 to PNG
    utils.log_info(f"Converting TM2: {os.path.basename(tm2_path)}")
    
    try:
        # Run gimconv
        result = subprocess.run(
            [gimconv_path, tm2_path, '-o', output_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            utils.log_info(f"Successfully converted to: {output_path}")
            return output_path
        else:
            utils.log_error(f"gimconv failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        utils.log_error(f"gimconv timeout for: {tm2_path}")
        return None
    except Exception as e:
        utils.log_error(f"gimconv error: {e}")
        return None


def load_texture(texture_path, texture_name=None):
    """
    Load texture into Blender
    
    Args:
        texture_path: Path to texture file
        texture_name: Optional name for the texture
    
    Returns:
        Blender Image object or None
    """
    if not os.path.exists(texture_path):
        utils.log_warning(f"Texture file not found: {texture_path}")
        return None
    
    if texture_name is None:
        texture_name = os.path.basename(texture_path)
    
    texture_name = utils.sanitize_name(texture_name)
    
    # Check if already loaded
    if texture_name in bpy.data.images:
        utils.log_debug(f"Texture already loaded: {texture_name}")
        return bpy.data.images[texture_name]
    
    # Load image
    try:
        utils.log_info(f"Loading texture: {os.path.basename(texture_path)}")
        image = bpy.data.images.load(texture_path)
        image.name = texture_name
        return image
    except Exception as e:
        utils.log_error(f"Failed to load texture {texture_path}: {e}")
        return None


def find_and_load_texture(gms_path, texture_name):
    """
    FIXED: Find texture file (TM2, PNG, or DDS) and load it
    Supports multiple fallback extensions
    
    Args:
        gms_path: Path to GMS file (to determine search directories)
        texture_name: Texture name from GMS file (without extension)
    
    Returns:
        Blender Image object or None
    """
    utils.log_debug(f"Looking for texture: {texture_name}")
    
    # FIXED: Find texture file with TM2/PNG/DDS support
    texture_path = utils.find_texture_file(gms_path, texture_name)
    
    if texture_path is None:
        utils.log_warning(f"Could not find texture: {texture_name} (searched TM2, PNG, DDS, JPG)")
        return None
    
    utils.log_info(f"Found texture file: {os.path.basename(texture_path)}")
    
    # Check if it's a TM2 file that needs conversion
    if texture_path.lower().endswith('.tm2'):
        utils.log_info(f"TM2 texture detected, attempting conversion...")
        
        # Convert to PNG
        png_path = convert_tm2_to_png(texture_path)
        
        if png_path:
            texture_path = png_path
            utils.log_info(f"TM2 converted successfully")
        else:
            utils.log_warning(f"Failed to convert TM2, texture will not be loaded: {texture_name}")
            return None
    
    # Load the texture (PNG, DDS, JPG, etc.)
    return load_texture(texture_path, texture_name)


def create_image_texture_node(material, image, location=(0, 0)):
    """
    Create an Image Texture node in the material
    
    Args:
        material: Blender material
        image: Blender Image object
        location: Node location (tuple of x, y)
    
    Returns:
        Image Texture node
    """
    if not material.use_nodes:
        material.use_nodes = True
    
    nodes = material.node_tree.nodes
    
    # Create Image Texture node
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = image
    tex_node.location = location
    
    return tex_node