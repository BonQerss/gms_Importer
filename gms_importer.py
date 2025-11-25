"""
Blender GMS Importer
Import .gms (text-based GMO) files into Blender
"""

bl_info = {
    "name": "GMS Format",
    "author": "GMS Importer",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "File > Import > GMS (.gms)",
    "description": "Import GMS (text-based GMO) files with proper skeleton and materials",
    "category": "Import-Export",
}

import bpy
import mathutils
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
import os
import sys

# Add the script directory to path to import modules
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import GMS modules
try:
    from . import gms_reader
    from . import import_gms
    from . import utils
except ImportError:
    # If running as standalone, try direct imports
    import importlib.util
    
    def load_module(module_name, file_name):
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(script_dir, file_name))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    gms_reader = load_module("gms_reader", "gms_reader.py")
    import_gms = load_module("import_gms", "import_gms.py")
    utils = load_module("utils", "utils.py")


class ImportGMS(bpy.types.Operator, ImportHelper):
    """Import GMS file with fixed skeleton and material support"""
    bl_idname = "import_scene.gms"
    bl_label = "Import GMS"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".gms"
    filter_glob: StringProperty(
        default="*.gms",
        options={'HIDDEN'},
    )
    
    # Import options
    import_textures: BoolProperty(
        name="Import Textures",
        description="Import and link textures (TM2, PNG, DDS)",
        default=True,
    )
    
    create_materials: BoolProperty(
        name="Create Materials",
        description="Create materials (even if textures not found)",
        default=True,
    )
    
    import_armature: BoolProperty(
        name="Import Armature",
        description="Import skeleton/bones",
        default=True,
    )
    
    apply_weights: BoolProperty(
        name="Apply Vertex Weights",
        description="Apply vertex weights for skinning",
        default=True,
    )
    
    coordinate_system: EnumProperty(
        name="Coordinate System",
        description="Target coordinate system",
        items=[
            ('BLENDER', "Blender (Z-up)", "Convert to Blender's Z-up coordinate system"),
            ('PSP', "PSP (Y-up)", "Keep original PSP Y-up coordinate system"),
        ],
        default='BLENDER',
    )
    
    scale_factor: FloatProperty(
        name="Scale",
        description="Scale factor for imported model",
        default=0.01,
        min=0.0001,
        max=100.0,
    )
    
    def execute(self, context):
        """Execute the import"""
        options = {
            'import_textures': self.import_textures,
            'create_materials': self.create_materials,
            'import_armature': self.import_armature,
            'apply_weights': self.apply_weights,
            'coordinate_system': self.coordinate_system,
            'scale_factor': self.scale_factor,
        }
        
        return import_gms.import_gms_file(self.filepath, context, **options)
    
    def draw(self, context):
        """Draw the import options UI"""
        layout = self.layout
        
        box = layout.box()
        box.label(text="Import Options:", icon='IMPORT')
        box.prop(self, "import_textures")
        box.prop(self, "create_materials")
        box.prop(self, "import_armature")
        box.prop(self, "apply_weights")
        
        box = layout.box()
        box.label(text="Transform Options:", icon='ORIENTATION_GIMBAL')
        box.prop(self, "coordinate_system")
        box.prop(self, "scale_factor")


def menu_func_import(self, context):
    """Add to File > Import menu"""
    self.layout.operator(ImportGMS.bl_idname, text="GMS (.gms)")


def register():
    """Register the addon"""
    bpy.utils.register_class(ImportGMS)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    print("[GMS Importer] Registered successfully")


def unregister():
    """Unregister the addon"""
    bpy.utils.unregister_class(ImportGMS)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    print("[GMS Importer] Unregistered")


if __name__ == "__main__":
    register()
    
    # For testing: import a file directly
    # bpy.ops.import_scene.gms(filepath="/path/to/your/file.gms")