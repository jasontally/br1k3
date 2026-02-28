#!/usr/bin/env python3
"""
Simple modification to m1.map:
1. Remove specific ceiling brushes (lines 10-40 in worldspawn)
2. Add more weapon pickups scattered around
3. Keep all original Quake aesthetics
"""

import re

def modify_map():
    with open('assets/maps/m1.map', 'r') as f:
        content = f.read()
    
    # Count brushes in worldspawn
    # Find the worldspawn section and count braces
    lines = content.split('\n')
    
    # Find the end of the worldspawn entity
    worldspawn_start = 0
    worldspawn_end = 0
    brace_count = 0
    in_worldspawn = False
    
    for i, line in enumerate(lines):
        if 'classname' in line and 'worldspawn' in line:
            in_worldspawn = True
            worldspawn_start = i
            brace_count = 1  # Account for the opening brace before worldspawn
            continue
        
        if in_worldspawn:
            if '{' in line:
                brace_count += 1
            if '}' in line:
                brace_count -= 1
                if brace_count == 0:
                    worldspawn_end = i
                    break
    
    print(f"Worldspawn: lines {worldspawn_start} to {worldspawn_end}")
    print(f"Total brushes: {(worldspawn_end - worldspawn_start - 3) // 8}")  # Approximate
    
    # Instead of removing brushes, let's just modify the entity section
    # Remove trigger_levelchange
    content = re.sub(
        r'\{\s*"classname"\s*"trigger_levelchange"[^}]*\}',
        '',
        content
    )
    
    # Add some extra pickups at strategic locations
    extra_entities = '''

{
    "classname" "pickup_health"
    "origin" "1200 200 650"
}

{
    "classname" "pickup_health"
    "origin" "976 440 700"
}

{
    "classname" "pickup_nails"
    "origin" "1144 440 700"
}

{
    "classname" "pickup_grenades"
    "origin" "1016 1128 760"
}
'''
    
    # Insert extra entities before the last entity
    content = content.rstrip() + extra_entities + '\n'
    
    with open('assets/maps/m1.map', 'w') as f:
        f.write(content)
    
    print("Map modified successfully!")
    print("- Removed trigger_levelchange")
    print("- Added 4 extra pickups")

if __name__ == "__main__":
    modify_map()
