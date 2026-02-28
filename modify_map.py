#!/usr/bin/env python3
"""
Modify m1.map to create an open arena courtyard
Removes ceiling brushes from the central area while keeping Quake aesthetic
"""

import re


def parse_face(line):
    """Parse a brush face line"""
    # Format: ( x y z ) ( x y z ) ( x y z ) tex_id offset_x offset_y rot scale_x scale_y
    match = re.match(
        r"\s*\(\s*([^)]+)\)\s*\(\s*([^)]+)\)\s*\(\s*([^)]+)\)\s*(.+)", line
    )
    if not match:
        return None

    p1 = [float(x) for x in match.group(1).split()]
    p2 = [float(x) for x in match.group(2).split()]
    p3 = [float(x) for x in match.group(3).split()]
    rest = match.group(4).strip().split()

    return {
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "tex_id": int(rest[0]) if rest else 0,
        "params": rest[1:] if len(rest) > 1 else [],
    }


def get_brush_bounds(faces):
    """Calculate brush bounds from faces"""
    all_points = []
    for face in faces:
        all_points.extend([face["p1"], face["p2"], face["p3"]])

    if not all_points:
        return None

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    min_z = min(p[2] for p in all_points)
    max_z = max(p[2] for p in all_points)

    return {
        "min": (min_x, min_y, min_z),
        "max": (max_x, max_y, max_z),
        "center": ((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2),
    }


def is_ceiling_brush(bounds):
    """Check if this brush is likely a ceiling in the courtyard area"""
    if not bounds:
        return False

    center = bounds["center"]
    min_z = bounds["min"][2]
    max_z = bounds["max"][2]

    # Courtyard area roughly: x: 700-1500, y: -300-800
    in_courtyard = 700 <= center[0] <= 1500 and -300 <= center[1] <= 800

    # Ceiling is high up (z > 600)
    is_high = min_z > 600

    # Brush is relatively thin (ceiling slabs less than 128 units thick)
    thickness = max_z - min_z
    is_thin = thickness < 128

    return in_courtyard and is_high and is_thin


def modify_map(input_file, output_file):
    """Modify the map to create open arena"""

    with open(input_file, "r") as f:
        content = f.read()

    lines = content.split("\n")
    output_lines = []

    in_brush = False
    current_brush_lines = []
    removed_count = 0
    kept_count = 0

    for line in lines:
        stripped = line.strip()

        # Start of brush
        if stripped == "{":
            in_brush = True
            current_brush_lines = [line]
            continue

        # End of brush
        if stripped == "}" and in_brush:
            current_brush_lines.append(line)
            in_brush = False

            # Parse brush faces
            faces = []
            for brush_line in current_brush_lines[1:-1]:  # Skip { and }
                face = parse_face(brush_line)
                if face:
                    faces.append(face)

            # Check if this is a ceiling to remove
            bounds = get_brush_bounds(faces)
            if bounds and is_ceiling_brush(bounds):
                removed_count += 1
                continue  # Skip this brush (remove ceiling)
            else:
                kept_count += 1
                output_lines.extend(current_brush_lines)

            continue

        # Inside brush
        if in_brush:
            current_brush_lines.append(line)
        else:
            output_lines.append(line)

    # Write output
    with open(output_file, "w") as f:
        f.write("\n".join(output_lines))

    print(f"Modified map written to: {output_file}")
    print(f"Removed {removed_count} ceiling brushes")
    print(f"Kept {kept_count} brushes")
    return removed_count, kept_count


if __name__ == "__main__":
    removed, kept = modify_map(
        "assets/maps/m1_backup_original.map", "assets/maps/m1.map"
    )
    print(f"\nMap modification complete!")
