"""
Quake .map format writer
Writes MapFile back to standard Quake .map format
"""
from .map_types import MapFile, Entity, Brush, Face, Vec3


def format_float(value: float) -> str:
    """Format float with reasonable precision"""
    # Remove trailing zeros and decimal point if not needed
    result = f"{value:.6f}"
    if '.' in result:
        result = result.rstrip('0').rstrip('.')
    return result


def write_face(face: Face) -> str:
    """Write a single face definition"""
    # Format: ( p1 ) ( p2 ) ( p3 ) texture u v rot su sv
    p1 = face.point1
    p2 = face.point2
    p3 = face.point3
    
    return (
        f"( {format_float(p1.x)} {format_float(p1.y)} {format_float(p1.z)} ) "
        f"( {format_float(p2.x)} {format_float(p2.y)} {format_float(p2.z)} ) "
        f"( {format_float(p3.x)} {format_float(p3.y)} {format_float(p3.z)} ) "
        f"{face.texture} "
        f"{format_float(face.offset_u)} "
        f"{format_float(face.offset_v)} "
        f"{format_float(face.rotation)} "
        f"{format_float(face.scale_u)} "
        f"{format_float(face.scale_v)}"
    )


def write_brush(brush: Brush, indent: str = "") -> str:
    """Write a brush definition with its faces"""
    lines = [f"{indent}{{"]
    
    for face in brush.faces:
        lines.append(f"{indent}    {write_face(face)}")
    
    lines.append(f"{indent}}}")
    
    return "\n".join(lines)


def write_entity(entity: Entity, index: int) -> str:
    """Write an entity with its properties and brushes"""
    lines = ["{"]
    
    # Write properties
    for key, value in entity.properties.items():
        # Escape quotes in value
        escaped_value = value.replace('"', '\\"')
        lines.append(f'    "{key}" "{escaped_value}"')
    
    # Write brushes
    for brush in entity.brushes:
        lines.append(write_brush(brush, indent="    "))
    
    lines.append("}")
    
    return "\n".join(lines)


def write_map_to_string(mapfile: MapFile) -> str:
    """Write complete map to string"""
    lines = []
    
    for i, entity in enumerate(mapfile.entities):
        if i > 0:
            lines.append("")  # Empty line between entities
        lines.append(write_entity(entity, i))
    
    return "\n".join(lines)


def write_map(mapfile: MapFile, filepath: str) -> None:
    """Write map to file"""
    content = write_map_to_string(mapfile)
    
    with open(filepath, 'w') as f:
        f.write(content)
        f.write("\n")  # Trailing newline


def write_map_file(mapfile: MapFile, filepath: str) -> None:
    """Alias for write_map"""
    write_map(mapfile, filepath)
