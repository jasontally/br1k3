"""
TrenchBroom-based map data structures
Ported from TrenchBroom's C++ model classes
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math


@dataclass
class Vec3:
    """3D vector with math operations - uses Z-up coordinate system"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __rmul__(self, scalar: float) -> 'Vec3':
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)
    
    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vec3') -> 'Vec3':
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def normalized(self) -> 'Vec3':
        length = self.length()
        if length < 1e-10:
            return Vec3(0, 0, 0)
        return self / length
    
    def distance(self, other: 'Vec3') -> float:
        return (self - other).length()
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]
    
    @staticmethod
    def from_list(coords: List[float]) -> 'Vec3':
        if len(coords) >= 3:
            return Vec3(coords[0], coords[1], coords[2])
        elif len(coords) == 2:
            return Vec3(coords[0], coords[1], 0.0)
        elif len(coords) == 1:
            return Vec3(coords[0], 0.0, 0.0)
        return Vec3(0.0, 0.0, 0.0)
    
    def __repr__(self) -> str:
        return f"Vec3({self.x}, {self.y}, {self.z})"


@dataclass
class Face:
    """Brush face with three points defining a plane"""
    point1: Vec3 = field(default_factory=Vec3)
    point2: Vec3 = field(default_factory=Vec3)
    point3: Vec3 = field(default_factory=Vec3)
    texture: str = ""
    offset_u: float = 0.0
    offset_v: float = 0.0
    rotation: float = 0.0
    scale_u: float = 1.0
    scale_v: float = 1.0
    
    def normal(self) -> Vec3:
        """Calculate face normal from three points"""
        v1 = self.point2 - self.point1
        v2 = self.point3 - self.point1
        return v1.cross(v2).normalized()
    
    def center(self) -> Vec3:
        """Calculate center point of the face triangle"""
        return (self.point1 + self.point2 + self.point3) / 3.0
    
    def move(self, offset: Vec3) -> None:
        """Move face by offset"""
        self.point1 = self.point1 + offset
        self.point2 = self.point2 + offset
        self.point3 = self.point3 + offset
    
    def copy(self) -> 'Face':
        """Create a copy of this face"""
        return Face(
            point1=Vec3(self.point1.x, self.point1.y, self.point1.z),
            point2=Vec3(self.point2.x, self.point2.y, self.point2.z),
            point3=Vec3(self.point3.x, self.point3.y, self.point3.z),
            texture=self.texture,
            offset_u=self.offset_u,
            offset_v=self.offset_v,
            rotation=self.rotation,
            scale_u=self.scale_u,
            scale_v=self.scale_v
        )
    
    def __repr__(self) -> str:
        return f"Face({self.point1}, {self.point2}, {self.point3}, texture='{self.texture}')"


@dataclass
class Brush:
    """Brush composed of multiple faces defining a convex volume"""
    faces: List[Face] = field(default_factory=list)
    
    def bounds(self) -> Tuple[Vec3, Vec3]:
        """Calculate axis-aligned bounding box (min, max)"""
        if not self.faces:
            return (Vec3(), Vec3())
        
        all_points = []
        for face in self.faces:
            all_points.extend([face.point1, face.point2, face.point3])
        
        min_vec = Vec3(
            min(p.x for p in all_points),
            min(p.y for p in all_points),
            min(p.z for p in all_points)
        )
        max_vec = Vec3(
            max(p.x for p in all_points),
            max(p.y for p in all_points),
            max(p.z for p in all_points)
        )
        return (min_vec, max_vec)
    
    def center(self) -> Vec3:
        """Calculate center of brush bounds"""
        min_b, max_b = self.bounds()
        return (min_b + max_b) / 2.0
    
    def move(self, offset: Vec3) -> None:
        """Move brush by offset"""
        for face in self.faces:
            face.move(offset)
    
    def copy(self) -> 'Brush':
        """Create a copy of this brush"""
        return Brush(faces=[face.copy() for face in self.faces])
    
    def face_count(self) -> int:
        return len(self.faces)
    
    def __repr__(self) -> str:
        return f"Brush({len(self.faces)} faces)"


@dataclass
class Entity:
    """Map entity with properties and optional brushes"""
    classname: str = ""
    properties: Dict[str, str] = field(default_factory=dict)
    brushes: List[Brush] = field(default_factory=list)
    
    def __post_init__(self):
        # Ensure classname is also in properties
        if self.classname:
            self.properties['classname'] = self.classname
    
    @property
    def origin(self) -> Optional[Vec3]:
        """Get origin from properties or calculate from brushes"""
        if 'origin' in self.properties:
            coords = self.properties['origin'].split()
            if len(coords) >= 3:
                return Vec3(float(coords[0]), float(coords[1]), float(coords[2]))
        
        # Calculate from brush centers
        if self.brushes:
            centers = [brush.center() for brush in self.brushes]
            avg = Vec3(
                sum(c.x for c in centers) / len(centers),
                sum(c.y for c in centers) / len(centers),
                sum(c.z for c in centers) / len(centers)
            )
            return avg
        
        return None
    
    @origin.setter
    def origin(self, value: Vec3) -> None:
        """Set origin property"""
        self.properties['origin'] = f"{int(value.x)} {int(value.y)} {int(value.z)}"
    
    def move_to(self, new_origin: Vec3) -> None:
        """Move entity to new origin, updating brushes"""
        current = self.origin
        if current and self.brushes:
            offset = new_origin - current
            for brush in self.brushes:
                brush.move(offset)
        
        self.origin = new_origin
    
    def get_property(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get property value with default"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: str) -> None:
        """Set property value"""
        self.properties[key] = value
        if key == 'classname':
            self.classname = value
    
    def brush_count(self) -> int:
        return len(self.brushes)
    
    def bounds(self) -> Optional[Tuple[Vec3, Vec3]]:
        """Calculate combined bounds of all brushes"""
        if not self.brushes:
            return None
        
        all_mins = []
        all_maxs = []
        for brush in self.brushes:
            bmin, bmax = brush.bounds()
            all_mins.append(bmin)
            all_maxs.append(bmax)
        
        min_vec = Vec3(
            min(p.x for p in all_mins),
            min(p.y for p in all_mins),
            min(p.z for p in all_mins)
        )
        max_vec = Vec3(
            max(p.x for p in all_maxs),
            max(p.y for p in all_maxs),
            max(p.z for p in all_maxs)
        )
        return (min_vec, max_vec)
    
    def copy(self) -> 'Entity':
        """Create a copy of this entity"""
        return Entity(
            classname=self.classname,
            properties=self.properties.copy(),
            brushes=[brush.copy() for brush in self.brushes]
        )
    
    def __repr__(self) -> str:
        return f"Entity({self.classname}, {len(self.brushes)} brushes, props={list(self.properties.keys())})"


@dataclass
class MapFile:
    """Complete Quake map file containing all entities"""
    entities: List[Entity] = field(default_factory=list)
    
    def worldspawn(self) -> Optional[Entity]:
        """Get the worldspawn entity (first entity with brushes)"""
        for entity in self.entities:
            if entity.classname == 'worldspawn' or entity.brushes:
                return entity
        return None
    
    def find_entities(self, classname: Optional[str] = None, property_key: Optional[str] = None,
                      property_value: Optional[str] = None) -> List[Entity]:
        """Find entities by criteria"""
        results = []
        for entity in self.entities:
            matches = True
            
            if classname and entity.classname != classname:
                matches = False
            
            if property_key:
                if property_key not in entity.properties:
                    matches = False
                elif property_value and entity.properties[property_key] != property_value:
                    matches = False
            
            if matches:
                results.append(entity)
        
        return results
    
    def get_entity_at_index(self, index: int) -> Optional[Entity]:
        """Get entity by index"""
        if 0 <= index < len(self.entities):
            return self.entities[index]
        return None
    
    def add_entity(self, entity: Entity) -> int:
        """Add entity to map, returns index"""
        self.entities.append(entity)
        return len(self.entities) - 1
    
    def remove_entity(self, index: int) -> bool:
        """Remove entity by index"""
        if 0 <= index < len(self.entities):
            self.entities.pop(index)
            return True
        return False
    
    def entity_count(self) -> int:
        return len(self.entities)
    
    def brush_count(self) -> int:
        return sum(len(e.brushes) for e in self.entities)
    
    def bounds(self) -> Optional[Tuple[Vec3, Vec3]]:
        """Calculate bounds of entire map"""
        if not self.entities:
            return None
        
        all_bounds = []
        for entity in self.entities:
            eb = entity.bounds()
            if eb:
                all_bounds.append(eb)
        
        if not all_bounds:
            return None
        
        min_vec = Vec3(
            min(b[0].x for b in all_bounds),
            min(b[0].y for b in all_bounds),
            min(b[0].z for b in all_bounds)
        )
        max_vec = Vec3(
            max(b[1].x for b in all_bounds),
            max(b[1].y for b in all_bounds),
            max(b[1].z for b in all_bounds)
        )
        return (min_vec, max_vec)
    
    def copy(self) -> 'MapFile':
        """Create a copy of this map"""
        return MapFile(entities=[entity.copy() for entity in self.entities])
    
    def __repr__(self) -> str:
        return f"MapFile({len(self.entities)} entities, {self.brush_count()} brushes)"
