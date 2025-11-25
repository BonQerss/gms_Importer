"""
Mesh builder for GMS importer - FIXED VERSION
Handles vertex weights with BlendSubset mapping and single-bone meshes
"""

import bpy
import bmesh
import mathutils
import math
from . import utils
from . import material_builder

def build_mesh_geometry(mesh_data, model, coordinate_system='BLENDER', scale=0.01):
    """
    Build mesh geometry from GMS data with proper coordinate conversion

    Args:
        mesh_data: Mesh object from gms_reader
        model: Model object containing arrays_dict
        coordinate_system: 'BLENDER' or 'PSP'
        scale: Scale factor

    Returns:
        (vertices, faces, uvs, normals, weights) tuple
    """
    vertices = []
    faces = []
    uvs = []
    normals = []
    weights = []

    utils.log_debug(f"Building geometry for mesh: {mesh_data.name}")
    utils.log_debug(f"  Draw commands: {len(mesh_data.draw_arrays)}")

    # Process each DrawArrays command
    for cmd_idx, draw_cmd in enumerate(mesh_data.draw_arrays):
        utils.log_debug(
            f"  Processing draw command {cmd_idx}: {draw_cmd.primitive_type}, "
            f"{draw_cmd.vertex_count_per_primitive} verts/prim, "
            f"{draw_cmd.primitive_count} primitives"
        )

        # Get vertex data
        if draw_cmd.arrays_name not in model.arrays_dict:
            utils.log_warning(f"Arrays '{draw_cmd.arrays_name}' not found")
            continue

        vertex_data = model.arrays_dict[draw_cmd.arrays_name]

        # Split indices into separate primitives
        primitives = []
        idx_offset = 0

        for prim_idx in range(draw_cmd.primitive_count):
            prim_start = idx_offset
            prim_end = idx_offset + draw_cmd.vertex_count_per_primitive
            prim_indices = draw_cmd.indices[prim_start:prim_end]
            primitives.append(prim_indices)
            idx_offset = prim_end

        # Process each primitive separately
        for prim_idx, prim_indices in enumerate(primitives):
            utils.log_debug(f"    Primitive {prim_idx}: {len(prim_indices)} indices")

            # Build vertex list for this primitive
            base_vertex_idx = len(vertices)
            prim_vertices = []
            prim_uvs = []
            prim_normals = []
            prim_weights = []

            for idx in prim_indices:
                if idx >= len(vertex_data.positions):
                    utils.log_warning(f"Vertex index {idx} out of range")
                    continue

                # Get position and convert coordinate system
                pos = vertex_data.positions[idx]
                pos_vec = utils.convert_coordinate_system([pos.x, pos.y, pos.z], coordinate_system)
                pos_vec = utils.apply_scale(pos_vec, scale)
                prim_vertices.append(pos_vec)

                # Get UV
                if idx < len(vertex_data.uvs):
                    uv = vertex_data.uvs[idx]
                    prim_uvs.append(uv)
                else:
                    prim_uvs.append((0.0, 0.0))

                # Get normal and convert coordinate system
                if idx < len(vertex_data.normals):
                    normal = vertex_data.normals[idx]
                    normal_vec = utils.convert_coordinate_system([normal.x, normal.y, normal.z], coordinate_system)
                    prim_normals.append(normal_vec.normalized())
                else:
                    prim_normals.append(mathutils.Vector((0, 0, 1)))

                # Get weights (store verbatim for later application)
                if idx < len(vertex_data.weights):
                    prim_weights.append(vertex_data.weights[idx])
                else:
                    prim_weights.append([])

            # Add vertices from this primitive
            vertices.extend(prim_vertices)
            uvs.extend(prim_uvs)
            normals.extend(prim_normals)
            weights.extend(prim_weights)

            # Build faces for this primitive
            prim_faces = build_faces_from_primitive(
                draw_cmd.primitive_type,
                list(range(len(prim_indices))),
                base_vertex_idx
            )

            faces.extend(prim_faces)

            utils.log_debug(f"      Added {len(prim_vertices)} vertices, {len(prim_faces)} faces")

    utils.log_info(f"Mesh geometry built: {len(vertices)} vertices, {len(faces)} faces")

    return vertices, faces, uvs, normals, weights

def build_faces_from_primitive(primitive_type, indices, base_idx=0):
    """
    Build faces from a single primitive

    Args:
        primitive_type: Type of primitive (TRIANGLES, TRIANGLE_STRIP, etc.)
        indices: List of vertex indices for this primitive
        base_idx: Base index to add to all indices

    Returns:
        List of face tuples
    """
    faces = []

    if primitive_type == "TRIANGLES":
        for i in range(0, len(indices) - 2, 3):
            faces.append((
                base_idx + indices[i],
                base_idx + indices[i + 1],
                base_idx + indices[i + 2]
            ))

    elif primitive_type == "TRIANGLE_STRIP":
        for i in range(len(indices) - 2):
            i0 = indices[i]
            i1 = indices[i + 1]
            i2 = indices[i + 2]

            # Skip degenerate triangles
            if i0 == i1 or i1 == i2 or i0 == i2:
                continue

            # Alternate winding to maintain proper face orientation
            if i % 2 == 0:
                faces.append((
                    base_idx + i0,
                    base_idx + i1,
                    base_idx + i2
                ))
            else:
                faces.append((
                    base_idx + i1,
                    base_idx + i0,
                    base_idx + i2
                ))

    elif primitive_type == "TRIANGLE_FAN":
        if len(indices) >= 3:
            center = base_idx + indices[0]
            for i in range(1, len(indices) - 1):
                faces.append((
                    center,
                    base_idx + indices[i],
                    base_idx + indices[i + 1]
                ))

    return faces

def create_mesh_object(mesh_data, model, context, coordinate_system='BLENDER', scale=0.01):
    """
    Create Blender mesh object from GMS mesh data

    Args:
        mesh_data: Mesh object from gms_reader
        model: Model object
        context: Blender context
        coordinate_system: 'BLENDER' or 'PSP'
        scale: Scale factor

    Returns:
        Blender mesh object
    """
    mesh_name = utils.sanitize_name(mesh_data.name)
    utils.log_info(f"Creating mesh: {mesh_name}")

    # Build geometry
    vertices, faces, uvs, normals, weights = build_mesh_geometry(
        mesh_data, model, coordinate_system, scale
    )

    if not vertices or not faces:
        utils.log_warning(f"No geometry for mesh: {mesh_name}")
        return None

    # Create mesh
    mesh = bpy.data.meshes.new(mesh_name)
    mesh_obj = bpy.data.objects.new(mesh_name, mesh)
    context.collection.objects.link(mesh_obj)

    # Build mesh from geometry
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Apply normals using Blender 4.x compatible method
    if normals and len(normals) == len(vertices):
        try:
            # Convert normals to tuple format for API
            normals_for_api = []
            for normal in normals:
                try:
                    normals_for_api.append((float(normal.x), float(normal.y), float(normal.z)))
                except AttributeError:
                    normals_for_api.append((float(normal[0]), float(normal[1]), float(normal[2])))

            # Use the proper API to set custom normals
            mesh.normals_split_custom_set_from_vertices(normals_for_api)

            # Enable auto smooth if available
            if hasattr(mesh, "use_auto_smooth"):
                try:
                    mesh.use_auto_smooth = True
                except Exception:
                    pass

            utils.log_debug(f"Applied {len(normals_for_api)} custom normals to {mesh_name}")
        except Exception as e:
            utils.log_warning(f"Failed to set custom normals: {e}")

    # Add UVs
    if uvs and len(uvs) == len(vertices):
        uv_layer = mesh.uv_layers.new(name="UVMap")

        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                if vert_idx < len(uvs):
                    # Flip V coordinate for Blender (V = 1 - V)
                    u, v = uvs[vert_idx]
                    uv_layer.data[loop_idx].uv = (u, 1.0 - v)

        utils.log_debug(f"Applied UVs to {mesh_name}")

    # Store weights and BlendSubset for later application
    mesh_obj['gms_weights'] = weights
    mesh_obj['gms_blend_subset'] = mesh_data.blend_subset

    utils.log_info(f"Created mesh object: {mesh_name}")
    return mesh_obj

def _iter_weight_entries(vert_weights):
    """
    Helper iterator that yields (bone_index, weight_value) pairs from
    various possible GMS weight formats.

    Supported formats:
    - list of (bone_index, weight_value) tuples -> [(14, 0.8), (32, 0.2)]
    - flat list of weights where index == bone index -> [0.0, 0.8, 0.0, ...]
    - empty / [] -> yields nothing
    """
    if not vert_weights:
        return
        yield  # make this a generator

    # Detect tuple-list format
    if isinstance(vert_weights, (list, tuple)) and len(vert_weights) > 0:
        first = vert_weights[0]
        # If first entry is a (bone_idx, weight) pair
        if (isinstance(first, (list, tuple)) and len(first) >= 2 and
                isinstance(first[0], int)):
            for entry in vert_weights:
                try:
                    bone_index = int(entry[0])
                    weight_value = float(entry[1])
                except Exception:
                    continue
                yield bone_index, weight_value
            return

    # Fallback: treat as flat list of weights
    for bone_index, weight_value in enumerate(vert_weights):
        try:
            w = float(weight_value)
        except Exception:
            continue
        yield bone_index, w

def apply_vertex_weights(mesh_obj, armature_obj, model, mesh_data):
    """
    Apply vertex weights to mesh for armature.
    Handles both weighted meshes and single-bone meshes with BlendSubset.
    

    CRITICAL: BlendSubset values are indices into a BlendBones array, NOT direct bone indices!

    Args:
        mesh_obj: Blender mesh object
        armature_obj: Blender armature object
        model: GMS Model object
        mesh_data: GMS Mesh object
    """
    if not mesh_obj or not armature_obj:
        return

    if 'gms_blend_subset' not in mesh_obj:
        utils.log_debug(f"No BlendSubset data for mesh: {mesh_obj.name}")
        return

    blend_subset = list(mesh_obj['gms_blend_subset'])
    weights = mesh_obj.get('gms_weights', [])

    utils.log_info(f"Applying vertex weights to {mesh_obj.name}")
    utils.log_debug(f"  Vertices: {len(mesh_obj.data.vertices)}, Bones: {len(model.bones)}")
    utils.log_debug(f"  BlendSubset: {blend_subset}")

    # Find the parent bone with BlendBones array for this mesh's part
    # Extract part name from mesh name (e.g., "body_0_Mesh" -> "body_0_Part")
    mesh_name_base = mesh_obj.name.replace("_Mesh", "_Part")
    parent_bone_name = model.part_to_bone.get(mesh_name_base)
    

    if not parent_bone_name:
        utils.log_warning(f"No parent bone found for part: {mesh_name_base}")
        return
    

    # Get the parent bone's BlendBones array
    parent_bone = None
    for bone in model.bones:
        if bone.name == parent_bone_name:
            parent_bone = bone
            break
    

    # Handle single-bone rigid meshes (no BlendBones, empty BlendSubset)
    # These use bone parenting instead of vertex weights, so skip them
    if not parent_bone or (not parent_bone.blend_bones and not blend_subset):
        utils.log_info(f"Skipping vertex weights for {mesh_obj.name} (rigid mesh using bone parenting)")
        return
    

    if not parent_bone.blend_bones:
        utils.log_warning(f"No BlendBones found for bone: {parent_bone_name}")
        return
    

    utils.log_debug(f"  Using BlendBones from: {parent_bone_name}")
    utils.log_debug(f"  BlendBones count: {len(parent_bone.blend_bones)}")

    # Create vertex groups by mapping BlendSubset through BlendBones
    bone_groups = {}
    existing_groups = {g.name: g for g in mesh_obj.vertex_groups}

    for local_bone_idx in blend_subset:
        # Map local index through BlendBones to get bone name
        if local_bone_idx < 0 or local_bone_idx >= len(parent_bone.blend_bones):
            utils.log_warning(f"BlendSubset index {local_bone_idx} out of range for BlendBones (size: {len(parent_bone.blend_bones)})")
            continue

        bone_name_from_blend = parent_bone.blend_bones[local_bone_idx]
        bone_name = utils.sanitize_name(bone_name_from_blend)

        if bone_name not in armature_obj.data.bones:
            utils.log_warning(f"Bone '{bone_name}' not found in armature")
            continue

        if bone_name in existing_groups:
            vg = existing_groups[bone_name]
        else:
            vg = mesh_obj.vertex_groups.new(name=bone_name)
            existing_groups[bone_name] = vg

        # Store with the LOCAL index from BlendSubset, not the global index
        bone_groups[local_bone_idx] = vg
        utils.log_debug(f"    Mapped local index {local_bone_idx} -> {bone_name}")

    # Case 1: Mesh has no weights but has BlendSubset with one bone
    # This is a single-bone mesh - assign all vertices to that bone with weight 1.0
    if (not weights or all(not w for w in weights)) and len(blend_subset) == 1:
        local_bone_idx = blend_subset[0]  # Use the actual BlendSubset value
        if local_bone_idx in bone_groups:
            vg = bone_groups[local_bone_idx]
            for vert_idx in range(len(mesh_obj.data.vertices)):
                vg.add([vert_idx], 1.0, 'REPLACE')
            utils.log_info(f"Applied {len(mesh_obj.data.vertices)} vertex weights to {mesh_obj.name} (single-bone mesh)")
        else:
            utils.log_info(f"Applied 0 vertex weights to {mesh_obj.name}")
    

    # Case 2: Mesh has weights - use local bone indices directly
    elif weights:
        weight_count = 0
        verts_len = len(mesh_obj.data.vertices)

        for vert_idx, vert_weights in enumerate(weights):
            if vert_idx >= verts_len:
                break

            if not vert_weights:
                continue

            # Iterate through weight bone indices
            # NOTE: These indices are positions in BlendSubset, NOT the actual bone indices
            for blend_subset_idx, weight_value in _iter_weight_entries(vert_weights):
                # Use this index to look up the actual local bone index from BlendSubset
                if blend_subset_idx < len(blend_subset):
                    actual_local_bone_idx = blend_subset[blend_subset_idx]
                    

                    # Apply weight if significant and vertex group exists
                    if weight_value > 0.0001 and actual_local_bone_idx in bone_groups:
                        try:
                            bone_groups[actual_local_bone_idx].add([vert_idx], weight_value, 'REPLACE')
                            weight_count += 1
                        except Exception as e:
                            utils.log_warning(f"Failed to add weight v{vert_idx} b{actual_local_bone_idx} w{weight_value}: {e}")

        utils.log_info(f"Applied {weight_count} vertex weights to {mesh_obj.name}")
    else:
        utils.log_info(f"Applied 0 vertex weights to {mesh_obj.name}")

    # Clean up temporary data
    try:
        del mesh_obj['gms_weights']
        del mesh_obj['gms_blend_subset']
    except Exception:
        pass