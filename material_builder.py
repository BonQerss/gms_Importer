"""
Material builder for GMS importer - FULLY FIXED VERSION v1.4
"""

import bpy
import os
from . import utils
from . import texture_utils


def create_material(material_data, model, gms_path, create_nodes=True, import_textures=True):
    """
    FIXED: Create Blender material from GMS material data
    Always creates the material even if textures aren't found
    Disables backface culling so both sides of faces are visible in viewport
    
    Args:
        material_data: Material object from gms_reader
        model: Model object from gms_reader (contains texture dict)
        gms_path: Path to GMS file (for texture lookup)
        create_nodes: Create shader nodes
        import_textures: Import and link textures
    
    Returns:
        Blender material object
    """
    mat_name = utils.sanitize_name(material_data.name)
    
    # Check if material already exists
    if mat_name in bpy.data.materials:
        utils.log_debug(f"Material already exists: {mat_name}")
        return bpy.data.materials[mat_name]
    
    # Create material
    utils.log_info(f"Creating material: {mat_name}")
    mat = bpy.data.materials.new(name=mat_name)
    
    # FIXED: Disable backface culling so both sides are visible
    mat.use_backface_culling = False
    # Enable show_transparent_back so backfaces are rendered
    mat.show_transparent_back = False
    mat.blend_method = 'OPAQUE'  # Force opaque rendering unless we add alpha textures
    
    if not create_nodes:
        # Simple material without nodes
        if material_data.diffuse:
            mat.diffuse_color = (
                material_data.diffuse.r,
                material_data.diffuse.g,
                material_data.diffuse.b,
                material_data.diffuse.a
            )
        return mat
    
    # Enable nodes
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Set base color from diffuse
    if material_data.diffuse:
        bsdf.inputs['Base Color'].default_value = (
            material_data.diffuse.r,
            material_data.diffuse.g,
            material_data.diffuse.b,
            material_data.diffuse.a
        )
    
    # Handle ambient as emission if it differs from diffuse
    if material_data.ambient:
        if material_data.diffuse:
            diff_r = abs(material_data.ambient.r - material_data.diffuse.r)
            diff_g = abs(material_data.ambient.g - material_data.diffuse.g)
            diff_b = abs(material_data.ambient.b - material_data.diffuse.b)
            
            if diff_r > 0.1 or diff_g > 0.1 or diff_b > 0.1:
                emission_strength = (material_data.ambient.r + material_data.ambient.g + material_data.ambient.b) / 3.0
                if 'Emission' in bsdf.inputs:
                    bsdf.inputs['Emission'].default_value = (
                        material_data.ambient.r,
                        material_data.ambient.g,
                        material_data.ambient.b,
                        1.0
                    )
                if 'Emission Strength' in bsdf.inputs:
                    bsdf.inputs['Emission Strength'].default_value = emission_strength * 0.5
    
    # Create output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Link BSDF to output
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # FIXED: Handle textures from layers - always create material even if texture not found
    texture_loaded = False
    if import_textures and material_data.layers:
        for layer in material_data.layers:
            if layer.texture_name:
                utils.log_info(f"Looking for texture: {layer.texture_name}")
                
                # Look up texture in model's texture dict to get filename
                texture_filename = None
                if layer.texture_name in model.texture_dict:
                    texture_idx = model.texture_dict[layer.texture_name]
                    if texture_idx < len(model.textures):
                        texture_obj = model.textures[texture_idx]
                        texture_filename = texture_obj.filename
                        utils.log_debug(f"Found texture filename: {texture_filename}")
                else:
                    # If not in dict, use the texture name directly as filename
                    texture_filename = layer.texture_name
                    utils.log_debug(f"Using texture name as filename: {texture_filename}")
                
                if texture_filename:
                    # Strip extension from filename before searching
                    texture_basename = os.path.splitext(texture_filename)[0]
                    
                    # FIXED: Find and load texture with TM2/PNG/DDS fallback
                    image = texture_utils.find_and_load_texture(gms_path, texture_basename)
                    
                    if image:
                        # Create texture node
                        texture_node = texture_utils.create_image_texture_node(
                            mat, image, location=(-300, 0)
                        )
                        
                        # Link texture to BSDF Base Color
                        links.new(texture_node.outputs['Color'], bsdf.inputs['Base Color'])
                        
                        # Link alpha if texture has alpha
                        if image.depth == 32:
                            links.new(texture_node.outputs['Alpha'], bsdf.inputs['Alpha'])
                            mat.blend_method = 'BLEND'
                            mat.shadow_method = 'HASHED'
                        
                        utils.log_info(f"✓ Texture linked: {texture_filename}")
                        texture_loaded = True
                    else:
                        utils.log_warning(f"✗ Texture not found: {texture_filename} (material still created)")
                
                break  # Use first texture for now
    
    if not texture_loaded and import_textures and material_data.layers:
        utils.log_info(f"Material '{mat_name}' created without texture - user can add texture manually")
    
    utils.log_debug(f"Material created successfully: {mat_name}")
    return mat


def apply_material_to_mesh(mesh_obj, material):
    """
    Apply material to mesh object
    
    Args:
        mesh_obj: Blender mesh object
        material: Blender material
    """
    if mesh_obj and material:
        if len(mesh_obj.data.materials) == 0:
            mesh_obj.data.materials.append(material)
        else:
            mesh_obj.data.materials[0] = material
        
        utils.log_debug(f"Applied material {material.name} to {mesh_obj.name}")


def get_or_create_material(material_name, model, gms_path, create_nodes=True, import_textures=True):
    """
    Get existing material or create new one
    
    Args:
        material_name: Name of material to get/create
        model: GMS Model object
        gms_path: Path to GMS file
        create_nodes: Create shader nodes
        import_textures: Import textures
    
    Returns:
        Blender material or None
    """
    if not material_name:
        return None
    
    # Check if already in Blender
    mat_name = utils.sanitize_name(material_name)
    if mat_name in bpy.data.materials:
        return bpy.data.materials[mat_name]
    
    # Find in model data
    if material_name in model.material_dict:
        mat_idx = model.material_dict[material_name]
        if mat_idx < len(model.materials):
            mat_data = model.materials[mat_idx]
            return create_material(mat_data, model, gms_path, create_nodes, import_textures)
    
    # FIXED: Create basic material even if not found in model data
    utils.log_warning(f"Material '{material_name}' not found in model, creating basic material")
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    # FIXED: Disable backface culling so both sides are visible
    mat.use_backface_culling = False
    mat.show_transparent_back = True
    return mat