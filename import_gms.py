import bpy
import mathutils
import math
from . import gms_reader
from . import mesh_builder
from . import material_builder
from . import utils


def create_armature(model, context, coordinate_system='BLENDER', scale=0.01):
    print("\n" + "="*60)
    print(">>> CREATE_ARMATURE CALLED <<<")
    print(f">>> Model: {model.name}")
    print(f">>> Bone count: {len(model.bones) if model.bones else 0}")
    print(f">>> Coordinate system: {coordinate_system}")
    print(f">>> Scale: {scale}")
    print("="*60 + "\n")
    
    if not model.bones:
        utils.log_info("No bones to create armature")
        return None
    
    utils.log_info(f"Creating armature with {len(model.bones)} bones")
    
    armature_name = utils.sanitize_name(model.name + "_Armature")
    armature = bpy.data.armatures.new(armature_name)
    armature_obj = bpy.data.objects.new(armature_name, armature)
    context.collection.objects.link(armature_obj)
    
    armature.display_type = 'OCTAHEDRAL'
    armature.show_names = False
    armature_obj.show_in_front = False
    
    context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    bone_map = {}
    edit_bones = armature.edit_bones
    bone_children = {}
    
    for bone_idx, bone_data in enumerate(model.bones):
        if bone_data.parent_name:
            if bone_data.parent_name not in bone_children:
                bone_children[bone_data.parent_name] = []
            bone_children[bone_data.parent_name].append(bone_idx)
    
    for bone_idx, bone_data in enumerate(model.bones):
        bone_name = utils.sanitize_name(bone_data.name)
        utils.log_debug(f"Creating bone {bone_idx}: {bone_name}")
        
        # Print detailed info for first 3 bones and any bone with "Bip01" in the name
        if bone_idx < 3 or "Bip01" in bone_name:
            print(f"\n>>> BONE {bone_idx}: {bone_name}")
            print(f"    Raw translation: ({bone_data.translation.x:.6f}, {bone_data.translation.y:.6f}, {bone_data.translation.z:.6f})")
            print(f"    Scale: {scale}")
            print(f"    Coordinate system: {coordinate_system}")
        
        edit_bone = edit_bones.new(bone_name)
        
        if bone_data.rotation_quaternion:
            quat = mathutils.Quaternion((
                bone_data.rotation_quaternion.w,
                bone_data.rotation_quaternion.x,
                bone_data.rotation_quaternion.y,
                bone_data.rotation_quaternion.z
            ))
            
            # Print rotation before invert
            if bone_idx < 3 or "Bip01" in bone_name:
                print(f"    Raw quaternion: ({quat.w:.6f}, {quat.x:.6f}, {quat.y:.6f}, {quat.z:.6f})")
            
            quat.invert()
            
            if bone_idx < 3 or "Bip01" in bone_name:
                print(f"    Inverted quaternion: ({quat.w:.6f}, {quat.x:.6f}, {quat.y:.6f}, {quat.z:.6f})")
            
            rot_euler = quat.to_euler('XYZ')
        else:
            rot_euler = mathutils.Euler((
                bone_data.rotation.x,
                bone_data.rotation.y,
                bone_data.rotation.z
            ), 'XYZ')
        
        if bone_idx < 3 or "Bip01" in bone_name:
            print(f"    Rotation euler: ({rot_euler.x:.6f}, {rot_euler.y:.6f}, {rot_euler.z:.6f})")
        
        # Scale translation - keep in PSP space
        scaled_trans_psp = mathutils.Vector((
            bone_data.translation.x * scale,
            bone_data.translation.y * scale,
            bone_data.translation.z * scale
        ))
        
        if bone_idx < 3 or "Bip01" in bone_name:
            print(f"    Scaled translation (PSP): ({scaled_trans_psp.x:.6f}, {scaled_trans_psp.y:.6f}, {scaled_trans_psp.z:.6f})")
        
        # Build local transform matrix in PSP space
        local_trans_matrix = mathutils.Matrix.Translation(scaled_trans_psp)
        local_rot_matrix = rot_euler.to_matrix().to_4x4()
        local_matrix_psp = local_trans_matrix @ local_rot_matrix
        
        # Calculate world transform by multiplying with parent's world matrix
        if bone_data.parent_name:
            parent_name = utils.sanitize_name(bone_data.parent_name)
            if parent_name in bone_map:
                parent_bone, parent_world_matrix_psp = bone_map[parent_name]
                
                # CRITICAL: Matrix multiply to properly transform through parent rotation
                world_matrix_psp = parent_world_matrix_psp @ local_matrix_psp
                
                if bone_idx < 3 or "Bip01" in bone_name:
                    print(f"    Parent world (PSP): {parent_world_matrix_psp.translation}")
                
                edit_bone.parent = parent_bone
                edit_bone.use_connect = False
            else:
                world_matrix_psp = local_matrix_psp
        else:
            world_matrix_psp = local_matrix_psp
        
        # Extract world position from matrix (still PSP space)
        world_pos_psp = world_matrix_psp.translation
        
        if bone_idx < 3 or "Bip01" in bone_name:
            print(f"    World (PSP): ({world_pos_psp.x:.6f}, {world_pos_psp.y:.6f}, {world_pos_psp.z:.6f})")
        
        # NOW convert final world position from PSP to Blender space
        if coordinate_system == 'BLENDER':
            world_pos_blender = utils.convert_coordinate_system(world_pos_psp)
        else:
            world_pos_blender = world_pos_psp
        
        # Build final transform with Blender position for bone display
        tfm = mathutils.Matrix.Translation(world_pos_blender)
        tfm = tfm @ rot_euler.to_matrix().to_4x4()
        
        head = world_pos_blender
        x_axis = tfm.to_3x3() @ mathutils.Vector((1, 0, 0))
        tail = head + x_axis.normalized() * (0.01 * scale)
        
        edit_bone.head = head
        edit_bone.tail = tail
        
        if bone_idx < 3 or "Bip01" in bone_name:
            print(f"    Final head (Blender): ({head.x:.6f}, {head.y:.6f}, {head.z:.6f})")
            if bone_data.parent_name:
                print(f"    Parent: {bone_data.parent_name}")
        
        bone_map[bone_name] = (edit_bone, world_matrix_psp)  # Store PSP world matrix for children
        utils.log_debug(f"  Created with head={head}, tail={tail}")
    
    for bone_idx, bone_data in enumerate(model.bones):
        edit_bone = edit_bones.get(utils.sanitize_name(bone_data.name))
        
        if bone_data.name in bone_children:
            child_idx = bone_children[bone_data.name][0]
            child_bone_data = model.bones[child_idx]
            child_bone = edit_bones.get(utils.sanitize_name(child_bone_data.name))
            
            if child_bone:
                direction = (child_bone.head - edit_bone.head)
                length = direction.length
                
                if length > 0.0001:
                    edit_bone.tail = edit_bone.head + direction.normalized() * length
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print("\n" + "="*60)
    print(f">>> CREATE_ARMATURE COMPLETE: {armature_name}")
    print(f">>> Final armature location: ({armature_obj.location.x:.6f}, {armature_obj.location.y:.6f}, {armature_obj.location.z:.6f})")
    print("="*60 + "\n")
    
    utils.log_info(f"Created armature: {armature_name}")
    return armature_obj


def align_model_to_floor(armature_obj, mesh_objects, context):
    print("\n" + "="*60)
    print(">>> ALIGN_MODEL_TO_FLOOR CALLED <<<")
    print(f">>> Armature: {armature_obj.name if armature_obj else 'None'}")
    print(f">>> Mesh count: {len(mesh_objects)}")
    if armature_obj:
        print(f">>> Armature location BEFORE: ({armature_obj.location.x:.6f}, {armature_obj.location.y:.6f}, {armature_obj.location.z:.6f})")
    print("="*60 + "\n")
    
    if not armature_obj:
        return
    
    bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.objects.active = armature_obj
    
    min_z = float('inf')
    
    for obj in mesh_objects:
        if obj and obj.type == 'MESH' and obj.data.vertices:
            matrix_world = obj.matrix_world
            for vert in obj.data.vertices:
                world_co = matrix_world @ vert.co
                if world_co.z < min_z:
                    min_z = world_co.z
    
    print(f">>> Minimum mesh Z found: {min_z:.6f}")
    
    if min_z != float('inf') and min_z < 0:
        offset = -min_z
        armature_obj.location.z -= min_z
        print(f">>> APPLYING OFFSET: {offset:.6f}")
        print(f">>> Armature location AFTER: ({armature_obj.location.x:.6f}, {armature_obj.location.y:.6f}, {armature_obj.location.z:.6f})")
        utils.log_info(f"Aligned model to floor (moved by {-min_z:.3f})")
    else:
        print(f">>> NO OFFSET APPLIED (min_z={min_z:.6f})")
    
    print("="*60 + "\n")


def import_gms_file(filepath, context, **options):
    utils.log_info("="*50)
    utils.log_info(f"Importing GMS file: {filepath}")
    utils.log_info("="*50)
    
    import_textures = options.get('import_textures', True)
    create_materials = options.get('create_materials', True)
    import_armature = options.get('import_armature', True)
    apply_weights = options.get('apply_weights', True)
    coordinate_system = options.get('coordinate_system', 'BLENDER')
    scale_factor = options.get('scale_factor', 0.01)
    
    utils.log_info(f"Options:")
    utils.log_info(f"  Import Textures: {import_textures}")
    utils.log_info(f"  Create Materials: {create_materials}")
    utils.log_info(f"  Import Armature: {import_armature}")
    utils.log_info(f"  Apply Weights: {apply_weights}")
    utils.log_info(f"  Coordinate System: {coordinate_system}")
    utils.log_info(f"  Scale Factor: {scale_factor}")
    
    try:
        utils.log_info("Reading GMS file...")
        model = gms_reader.read_gms_file(filepath)
        
        utils.log_info(f"Loaded model: {model.name}")
        utils.log_info(f"  Bones: {len(model.bones)}")
        utils.log_info(f"  Parts: {len(model.parts)}")
        utils.log_info(f"  Materials: {len(model.materials)}")
        utils.log_info(f"  Textures: {len(model.textures)}")
        utils.log_info(f"  Arrays: {len(model.arrays_dict)}")
        
        armature_obj = None
        if import_armature and model.bones:
            print("\n*** CALLING create_armature from import_gms_file ***\n")
            armature_obj = create_armature(model, context, coordinate_system, scale_factor)
            if armature_obj:
                print(f"\n*** Armature created, object location: ({armature_obj.location.x:.6f}, {armature_obj.location.y:.6f}, {armature_obj.location.z:.6f}) ***\n")
        
        material_cache = {}
        if create_materials:
            utils.log_info("Creating materials...")
            for mat_data in model.materials:
                try:
                    mat = material_builder.create_material(
                        mat_data,
                        model,
                        filepath,
                        create_nodes=True,
                        import_textures=import_textures
                    )
                    material_cache[mat_data.name] = mat
                    utils.log_info(f"  Created material: {mat_data.name}")
                except Exception as e:
                    utils.log_error(f"Failed to create material {mat_data.name}: {e}")
                    mat = bpy.data.materials.new(name=utils.sanitize_name(mat_data.name))
                    mat.use_nodes = True
                    mat.use_backface_culling = True
                    if mat_data.diffuse:
                        mat.diffuse_color = (
                            mat_data.diffuse.r,
                            mat_data.diffuse.g,
                            mat_data.diffuse.b,
                            mat_data.diffuse.a
                        )
                    material_cache[mat_data.name] = mat
                    utils.log_info(f"  Created fallback material: {mat_data.name}")
        
        mesh_objects = []
        utils.log_info("Creating meshes...")
        
        for part_idx, part in enumerate(model.parts):
            utils.log_info(f"Processing part {part_idx + 1}/{len(model.parts)}: {part.name}")
            
            for mesh_data in part.meshes:
                mesh_obj = mesh_builder.create_mesh_object(
                    mesh_data,
                    model,
                    context,
                    coordinate_system,
                    scale_factor
                )
                
                if mesh_obj:
                    mesh_objects.append(mesh_obj)
                    
                    if create_materials and mesh_data.material_name:
                        if mesh_data.material_name in material_cache:
                            mat = material_cache[mesh_data.material_name]
                            material_builder.apply_material_to_mesh(mesh_obj, mat)
                            utils.log_debug(f"  Applied material {mat.name} to {mesh_obj.name}")
                    
                    if armature_obj:
                        mesh_name_base = mesh_obj.name.replace("_Mesh", "_Part")
                        parent_bone_name = model.part_to_bone.get(mesh_name_base)
                        is_rigid_mesh = False
                        
                        if parent_bone_name:
                            parent_bone = None
                            for bone in model.bones:
                                if bone.name == parent_bone_name:
                                    parent_bone = bone
                                    break
                            
                            if parent_bone and not parent_bone.blend_bones and not mesh_data.blend_subset:
                                is_rigid_mesh = True
                                bone_name = utils.sanitize_name(parent_bone_name)
                                if bone_name in armature_obj.data.bones:
                                    mesh_obj.parent = armature_obj
                                    mesh_obj.parent_type = 'BONE'
                                    mesh_obj.parent_bone = bone_name
                                    utils.log_debug(f"Parented {mesh_obj.name} to bone {bone_name} (rigid)")
                        
                        if not is_rigid_mesh:
                            mesh_obj.parent = armature_obj
                            modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
                            modifier.object = armature_obj
                            utils.log_debug(f"Parented {mesh_obj.name} to armature (skinned)")
        
        if apply_weights and armature_obj:
            utils.log_info("Applying vertex weights...")
            for part in model.parts:
                for mesh_data in part.meshes:
                    mesh_name = utils.sanitize_name(mesh_data.name)
                    mesh_obj = bpy.data.objects.get(mesh_name)
                    if mesh_obj:
                        mesh_builder.apply_vertex_weights(mesh_obj, armature_obj, model, mesh_data)
        
        
        if armature_obj and mesh_objects:
            align_model_to_floor(armature_obj, mesh_objects, context)
        
        utils.log_info("="*50)
        utils.log_info(f"Import complete!")
        utils.log_info(f"  Created {len(mesh_objects)} meshes")
        if armature_obj:
            utils.log_info(f"  Created armature with {len(model.bones)} bones")
        utils.log_info(f"  Created {len(material_cache)} materials")
        utils.log_info("="*50)
        
        return {'FINISHED'}
        
    except Exception as e:
        utils.log_error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        return {'CANCELLED'}