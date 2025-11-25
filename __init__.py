"""
GMS Importer - Import PlayStation Portable GMO model files (text format)
"""

bl_info = {
    "name": "GMS Importer",
    "author": "GMS Importer Team",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "File > Import > GMS (.gms)",
    "description": "Import GMS (text-based GMO) files with full texture and material support",
    "warning": "",
    "category": "Import-Export",
}

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy_extras.io_utils import ImportHelper

# Import our modules
if "bpy" in locals():
    import importlib
    if "import_gms" in locals():
        importlib.reload(import_gms)
    if "gms_reader" in locals():
        importlib.reload(gms_reader)
    if "mesh_builder" in locals():
        importlib.reload(mesh_builder)
    if "material_builder" in locals():
        importlib.reload(material_builder)
    if "texture_utils" in locals():
        importlib.reload(texture_utils)
    if "utils" in locals():
        importlib.reload(utils)
else:
    from . import import_gms
    from . import gms_reader
    from . import mesh_builder
    from . import material_builder
    from . import texture_utils
    from . import utils


class ImportGMS(bpy.types.Operator, ImportHelper):
    """Import GMS file with textures and materials"""
    bl_idname = "import_scene.gms"
    bl_label = "Import GMS"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    
    filename_ext = ".gms"
    filter_glob: StringProperty(
        default="*.gms",
        options={'HIDDEN'},
    )
    
    import_textures: BoolProperty(
        name="Import Textures",
        description="Automatically import and convert textures (TM2/PNG)",
        default=True,
    )
    
    create_materials: BoolProperty(
        name="Create Materials",
        description="Create materials with proper shader nodes",
        default=True,
    )
    
    import_armature: BoolProperty(
        name="Import Armature",
        description="Create armature from bone data",
        default=True,
    )
    
    apply_weights: BoolProperty(
        name="Apply Vertex Weights",
        description="Apply bone weights to meshes",
        default=True,
    )
    
    coordinate_system: EnumProperty(
        name="Coordinate System",
        description="Coordinate system conversion",
        items=[
            ('PSP', "PSP (Original)", "Use original PSP coordinate system"),
            ('BLENDER', "Blender (Z-up)", "Convert to Blender Z-up coordinate system"),
        ],
        default='BLENDER',
    )
    
    scale_factor: FloatProperty(
        name="Scale",
        description="Scale factor for import",
        default=0.01,
        min=0.001,
        max=100.0,
    )
    
    def execute(self, context):
        from . import import_gms
        return import_gms.import_gms_file(
            self.filepath,
            context,
            import_textures=self.import_textures,
            create_materials=self.create_materials,
            import_armature=self.import_armature,
            apply_weights=self.apply_weights,
            coordinate_system=self.coordinate_system,
            scale_factor=self.scale_factor,
        )


def menu_func_import(self, context):
    self.layout.operator(ImportGMS.bl_idname, text="GMS (.gms)")


def register():
    bpy.utils.register_class(ImportGMS)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGMS)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()