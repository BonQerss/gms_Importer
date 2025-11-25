"""
GMS File Reader - Text-based GMO format reader
GMS files are GMO files exported as text format
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


class InterpolationType(Enum):
    CONSTANT = 0
    LINEAR = 1
    HERMITE = 2
    CUBIC = 3
    SPHERICAL = 4


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    @classmethod
    def from_string(cls, line: str):
        """Parse 'x y z' from string"""
        parts = line.strip().split()
        return cls(float(parts[0]), float(parts[1]), float(parts[2]))


@dataclass
class Vector4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0
    
    @classmethod
    def from_string(cls, line: str):
        """Parse 'x y z w' from string"""
        parts = line.strip().split()
        return cls(float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


@dataclass
class Color:
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0
    
    @classmethod
    def from_string(cls, line: str):
        """Parse 'r g b a' from string"""
        parts = line.strip().split()
        return cls(float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


@dataclass
class BoundingBox:
    min: Vector3 = field(default_factory=Vector3)
    max: Vector3 = field(default_factory=Vector3)


@dataclass
class BlindData:
    name: str = ""
    data_count: int = 0
    values: List[int] = field(default_factory=list)


@dataclass
class Bone:
    name: str = ""
    parent_name: Optional[str] = None
    translation: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    rotation_quaternion: Optional[Vector4] = None
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))
    blind_data: Optional[BlindData] = None
    blend_bones: List[str] = field(default_factory=list)


@dataclass
class VertexData:
    positions: List[Vector3] = field(default_factory=list)
    normals: List[Vector3] = field(default_factory=list)
    colors: List[Color] = field(default_factory=list)
    uvs: List[Tuple[float, float]] = field(default_factory=list)
    weights: List[List[float]] = field(default_factory=list)
    bone_indices: List[List[int]] = field(default_factory=list)


@dataclass
class DrawArraysCommand:
    arrays_name: str = ""
    primitive_type: str = ""
    vertex_count: int = 0
    vertex_count_per_primitive: int = 0
    primitive_count: int = 0
    indices: List[int] = field(default_factory=list)


@dataclass
class Mesh:
    name: str = ""
    material_name: Optional[str] = None
    draw_arrays: List[DrawArraysCommand] = field(default_factory=list)
    part_arrays: Dict[str, VertexData] = field(default_factory=dict)
    blend_subset: List[int] = field(default_factory=list)


@dataclass
class Layer:
    name: str = ""
    diffuse: Optional[Color] = None
    ambient: Optional[Color] = None
    specular: Optional[Color] = None
    emission: Optional[Color] = None
    texture_name: Optional[str] = None
    meshes: List[Mesh] = field(default_factory=list)


@dataclass
class Material:
    name: str = ""
    diffuse: Optional[Color] = None
    ambient: Optional[Color] = None
    layers: List[Layer] = field(default_factory=list)


@dataclass
class FCurveFrame:
    time: float = 0.0
    values: List[float] = field(default_factory=list)


@dataclass
class FCurve:
    name: str = ""
    interpolation_type: InterpolationType = InterpolationType.LINEAR
    value_count: int = 0
    frame_count: int = 0
    frames: List[FCurveFrame] = field(default_factory=list)


@dataclass
class Motion:
    name: str = ""
    fcurves: List[FCurve] = field(default_factory=list)
    frame_rate: float = 30.0
    frame_loop: Tuple[float, float] = (0.0, 0.0)


@dataclass
class Part:
    name: str = ""
    meshes: List[Mesh] = field(default_factory=list)
    parent_bone_index: int = -1
    parent_bone_name: Optional[str] = None  # Name of parent bone that owns BlendBones


@dataclass
class Texture:
    name: str = ""
    filename: str = ""


@dataclass
class Model:
    name: str = ""
    bounding_box: Optional[BoundingBox] = None
    bones: List[Bone] = field(default_factory=list)
    bone_dict: Dict[str, int] = field(default_factory=dict)
    parts: List[Part] = field(default_factory=list)
    materials: List[Material] = field(default_factory=list)
    material_dict: Dict[str, int] = field(default_factory=dict)
    textures: List[Texture] = field(default_factory=list)
    texture_dict: Dict[str, int] = field(default_factory=dict)
    motions: List[Motion] = field(default_factory=list)
    arrays_dict: Dict[str, VertexData] = field(default_factory=dict)
    part_to_bone: Dict[str, str] = field(default_factory=dict)  # Part name -> Bone name with BlendBones


class GMSReader:
    """Reader for GMS (text-based GMO) files"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.lines: List[str] = []
        self.current_line = 0
        self.model = Model()
        
    def read_file(self) -> Model:
        """Main entry point to read a GMS file"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()
        
        self.current_line = 0
        
        # Check header
        if not self.lines[0].startswith('.GMS'):
            raise ValueError("Not a valid GMS file - missing .GMS header")
        
        self.current_line = 1
        
        # Read top-level blocks
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            # Skip Define statements and BlindData for now
            if line.startswith('DefineEnum') or line.startswith('DefineBlock') or \
               line.startswith('DefineCommand') or line.startswith('BlindData'):
                self.current_line += 1
                continue
            
            # Parse Model block
            if line.startswith('Model'):
                self.model = self._parse_model()
                break
            
            self.current_line += 1
        
        return self.model
    
    def _peek_line(self, offset: int = 0) -> str:
        """Peek at a line without advancing"""
        idx = self.current_line + offset
        if idx < len(self.lines):
            return self.lines[idx].strip()
        return ""
    
    def _read_line(self) -> str:
        """Read current line and advance"""
        if self.current_line < len(self.lines):
            line = self.lines[self.current_line].strip()
            self.current_line += 1
            return line
        return ""
    
    def _extract_name(self, line: str) -> Optional[str]:
        """Extract name from line like: Bone "bonename" {"""
        match = re.search(r'"([^"]+)"', line)
        return match.group(1) if match else None
    
    def _parse_model(self) -> Model:
        """Parse Model block"""
        model = Model()
        self.model = model
        line = self._read_line()
        model.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        brace_depth = 1
        
        while self.current_line < len(self.lines) and brace_depth > 0:
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                brace_depth -= 1
                self.current_line += 1
                if brace_depth == 0:
                    break
                continue
            elif line.endswith('{') and not any(line.startswith(kw) for kw in 
                ['BoundingBox', 'Translate', 'RotateZYX', 'RotateYXZ', 'RotateQ', 'Scale', 
                 'ParentBone', 'Pivot', 'BlindData', 'Diffuse', 'Ambient', 'Specular', 
                 'Emission', 'SetTexture', 'SetMaterial', 'DrawArrays', 'BlendFunc', 
                 'FrameRate', 'FrameLoop', 'FileName']):
                pass
            
            if line.startswith('BoundingBox'):
                model.bounding_box = self._parse_bounding_box()
            elif line.startswith('Bone'):
                bone = self._parse_bone()
                model.bones.append(bone)
                model.bone_dict[bone.name] = len(model.bones) - 1
            elif line.startswith('Part'):
                part = self._parse_part()
                model.parts.append(part)
            elif line.startswith('Material'):
                material = self._parse_material()
                model.materials.append(material)
                model.material_dict[material.name] = len(model.materials) - 1
            elif line.startswith('Texture'):
                texture = self._parse_texture()
                model.textures.append(texture)
                model.texture_dict[texture.name] = len(model.textures) - 1
            elif line.startswith('Motion'):
                motion = self._parse_motion()
                model.motions.append(motion)
            else:
                self.current_line += 1
        
        return model
    
    def _parse_bounding_box(self) -> BoundingBox:
        """Parse BoundingBox line"""
        line = self._read_line()
        parts = line.split()[1:]
        bb = BoundingBox()
        bb.min = Vector3(float(parts[0]), float(parts[1]), float(parts[2]))
        bb.max = Vector3(float(parts[3]), float(parts[4]), float(parts[5]))
        return bb
    
    def _parse_bone(self) -> Bone:
        """Parse Bone block"""
        bone = Bone()
        line = self._read_line()
        bone.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('ParentBone'):
                self._read_line()
                bone.parent_name = self._extract_name(line)
            elif line.startswith('Translate'):
                self._read_line()
                parts = line.split()[1:]
                bone.translation = Vector3(float(parts[0]), float(parts[1]), float(parts[2]))
            elif line.startswith('RotateZYX') or line.startswith('RotateYXZ'):
                self._read_line()
                parts = line.split()[1:]
                bone.rotation = Vector3(float(parts[0]), float(parts[1]), float(parts[2]))
            elif line.startswith('RotateQ'):
                self._read_line()
                parts = line.split()[1:]
                bone.rotation_quaternion = Vector4(float(parts[0]), float(parts[1]), 
                                                   float(parts[2]), float(parts[3]))
            elif line.startswith('Scale'):
                self._read_line()
                parts = line.split()[1:]
                bone.scale = Vector3(float(parts[0]), float(parts[1]), float(parts[2]))
            elif line.startswith('BlendBones'):
                self._read_line()
                # Format: BlendBones <count> "bone_name1" "bone_name2" ...
                # Extract all quoted bone names from the line
                bone.blend_bones = re.findall(r'"([^"]+)"', line)
            elif line.startswith('DrawPart'):
                self._read_line()
                # Format: DrawPart "part_name"
                # Link this Part to this Bone's BlendBones
                part_name = self._extract_name(line)
                if part_name and hasattr(self, 'model') and self.model:
                    self.model.part_to_bone[part_name] = bone.name
            else:
                self.current_line += 1
        
        return bone
    
    def _parse_part(self) -> Part:
        """Parse Part block"""
        part = Part()
        line = self._read_line()
        part.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        part_arrays = {}
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('BoundingBox'):
                self.current_line += 1
            elif line.startswith('Mesh'):
                mesh = self._parse_mesh()
                part.meshes.append(mesh)
            elif line.startswith('Arrays'):
                arr_name, arr_data = self._parse_arrays()
                part_arrays[arr_name] = arr_data
                if hasattr(self, 'model') and self.model:
                    self.model.arrays_dict[arr_name] = arr_data
            else:
                self.current_line += 1
        
        for mesh in part.meshes:
            mesh.part_arrays = part_arrays
        
        return part
    
    def _parse_arrays(self) -> Tuple[str, VertexData]:
        """Parse Arrays block and return (name, VertexData)"""
        line = self._read_line()
        arr_name = self._extract_name(line) or ""
        
        parts = line.split()
        vertex_count = 0
        format_flags = ""
        
        for i, part in enumerate(parts):
            if '|' in part or part in ['VERTEX', 'NORMAL', 'TEXCOORD', 'COLOR', 'WEIGHT1', 'WEIGHT2', 'WEIGHT3', 'WEIGHT4', 'WEIGHT5', 'WEIGHT6', 'WEIGHT7', 'WEIGHT8']:
                format_flags = part
                if i + 1 < len(parts) and parts[i + 1].isdigit():
                    vertex_count = int(parts[i + 1])
                break
        
        has_vertex = 'VERTEX' in format_flags
        has_normal = 'NORMAL' in format_flags
        has_texcoord = 'TEXCOORD' in format_flags
        has_color = 'COLOR' in format_flags
        
        weight_count = 0
        for i in range(1, 9):
            if f'WEIGHT{i}' in format_flags:
                weight_count = i
                break
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        vertex_data = VertexData()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            self._read_line()
            values = [float(v) for v in line.split()]
            idx = 0
            
            if has_vertex and idx + 3 <= len(values):
                vertex_data.positions.append(Vector3(values[idx], values[idx + 1], values[idx + 2]))
                idx += 3
            
            if has_normal and idx + 3 <= len(values):
                vertex_data.normals.append(Vector3(values[idx], values[idx + 1], values[idx + 2]))
                idx += 3
            
            if has_texcoord and idx + 2 <= len(values):
                vertex_data.uvs.append((values[idx], values[idx + 1]))
                idx += 2
            
            if has_color and idx + 4 <= len(values):
                vertex_data.colors.append(Color(values[idx], values[idx + 1], values[idx + 2], values[idx + 3]))
                idx += 4
            
            if weight_count > 0 and idx + weight_count <= len(values):
                weights = [values[idx + i] for i in range(weight_count)]
                vertex_data.weights.append(weights)
        
        return arr_name, vertex_data
    
    def _parse_material(self) -> Material:
        """Parse Material block"""
        material = Material()
        line = self._read_line()
        material.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('Diffuse'):
                self._read_line()
                parts = line.split()[1:]
                if len(parts) >= 4:
                    material.diffuse = Color(float(parts[0]), float(parts[1]), 
                                           float(parts[2]), float(parts[3]))
            elif line.startswith('Ambient'):
                self._read_line()
                parts = line.split()[1:]
                if len(parts) >= 4:
                    material.ambient = Color(float(parts[0]), float(parts[1]), 
                                           float(parts[2]), float(parts[3]))
            elif line.startswith('Layer'):
                layer = self._parse_layer()
                material.layers.append(layer)
            elif line.startswith('BlindData') or line.startswith('RenderState'):
                self.current_line += 1
            else:
                self.current_line += 1
        
        return material
    
    def _parse_layer(self) -> Layer:
        """Parse Layer block"""
        layer = Layer()
        line = self._read_line()
        layer.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('Diffuse'):
                self._read_line()
                parts = line.split()[1:]
                layer.diffuse = Color(float(parts[0]), float(parts[1]), 
                                    float(parts[2]), float(parts[3]))
            elif line.startswith('Ambient'):
                self._read_line()
                parts = line.split()[1:]
                layer.ambient = Color(float(parts[0]), float(parts[1]), 
                                    float(parts[2]), float(parts[3]))
            elif line.startswith('Specular'):
                self._read_line()
                parts = line.split()[1:]
                layer.specular = Color(float(parts[0]), float(parts[1]), 
                                      float(parts[2]), float(parts[3]))
            elif line.startswith('Emission'):
                self._read_line()
                parts = line.split()[1:]
                layer.emission = Color(float(parts[0]), float(parts[1]), 
                                      float(parts[2]), float(parts[3]))
            elif line.startswith('SetTexture'):
                self._read_line()
                layer.texture_name = self._extract_name(line)
            elif line.startswith('BlendFunc'):
                self.current_line += 1
            elif line.startswith('Mesh'):
                mesh = self._parse_mesh()
                layer.meshes.append(mesh)
            else:
                self.current_line += 1
        
        return layer
    
    def _parse_mesh(self) -> Mesh:
        """Parse Mesh block"""
        mesh = Mesh()
        line = self._read_line()
        mesh.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('SetMaterial'):
                self._read_line()
                mesh.material_name = self._extract_name(line)
            elif line.startswith('BlendSubset'):
                self._read_line()
                # Parse BlendSubset: "BlendSubset <count> <bone_idx1> <bone_idx2> ..."
                parts = line.split()
                if len(parts) >= 2:
                    count = int(parts[1])
                    bone_indices = []
                    for i in range(2, 2 + count):
                        if i < len(parts):
                            bone_indices.append(int(parts[i]))
                    mesh.blend_subset = bone_indices
            elif line.startswith('DrawArrays'):
                draw_cmd = self._parse_draw_arrays()
                mesh.draw_arrays.append(draw_cmd)
            else:
                self.current_line += 1
        
        return mesh
    
    def _parse_draw_arrays(self) -> DrawArraysCommand:
        """Parse DrawArrays command line"""
        line = self._read_line()
        draw_cmd = DrawArraysCommand()
        
        draw_cmd.arrays_name = self._extract_name(line) or ""
        
        parts = line.split()
        
        vertex_count_per_prim = 0
        primitive_count = 0
        
        # Known primitive types (with or without PRIM_ prefix)
        primitive_types = ['TRIANGLES', 'TRIANGLE_STRIP', 'TRIANGLE_FAN', 'POINTS', 'LINES', 'LINE_STRIP']
        
        for i, part in enumerate(parts):
            # Check if this part is a primitive type (with or without PRIM_ prefix)
            prim_type = part.replace('PRIM_', '') if part.startswith('PRIM_') else part
            
            if prim_type in primitive_types:
                draw_cmd.primitive_type = prim_type
                if i + 1 < len(parts) and parts[i + 1].isdigit():
                    vertex_count_per_prim = int(parts[i + 1])
                if i + 2 < len(parts) and parts[i + 2].isdigit():
                    primitive_count = int(parts[i + 2])
                
                indices_start = i + 3
                for j in range(indices_start, len(parts)):
                    try:
                        draw_cmd.indices.append(int(parts[j]))
                    except ValueError:
                        pass
                break
        
        draw_cmd.vertex_count = vertex_count_per_prim * primitive_count
        draw_cmd.vertex_count_per_primitive = vertex_count_per_prim
        draw_cmd.primitive_count = primitive_count
        
        return draw_cmd
    
    def _parse_texture(self) -> Texture:
        """Parse Texture block"""
        texture = Texture()
        line = self._read_line()
        texture.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('FileName'):
                self._read_line()
                filename = self._extract_name(line)
                if filename:
                    texture.filename = filename
            else:
                self.current_line += 1
        
        return texture
    
    def _parse_motion(self) -> Motion:
        """Parse Motion block"""
        motion = Motion()
        line = self._read_line()
        motion.name = self._extract_name(line) or ""
        
        if not line.rstrip().endswith('{'):
            self._read_line()
        
        while self.current_line < len(self.lines):
            line = self._peek_line()
            
            if not line or line.startswith('//'):
                self.current_line += 1
                continue
            
            if line == '}':
                self.current_line += 1
                break
            
            if line.startswith('FrameRate'):
                self._read_line()
                motion.frame_rate = float(line.split()[1])
            elif line.startswith('FrameLoop'):
                self._read_line()
                parts = line.split()[1:]
                motion.frame_loop = (float(parts[0]), float(parts[1]))
            elif line.startswith('FCurve') or line.startswith('Animate'):
                self.current_line += 1
            else:
                self.current_line += 1
        
        return motion


def read_gms_file(filepath: str) -> Model:
    """Read a GMS file and return a Model object"""
    reader = GMSReader(filepath)
    return reader.read_file()