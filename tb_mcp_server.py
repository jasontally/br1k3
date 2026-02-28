#!/usr/bin/env python3
"""
TrenchBroom-based MCP Map Editor Server for Q1K3
Provides programmatic control of Quake .map files via MCP protocol
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add parent directory to path for tb_mcp imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from sse_starlette.sse import EventSourceResponse

from tb_mcp.map_types import MapFile, Entity, Brush, Vec3
from tb_mcp.map_parser import parse_map, parse_map_file, ParseError
from tb_mcp.map_writer import write_map, write_map_to_string

# Configuration
PROJECT_DIR = Path("/Users/jtally/s1k3")
MAPS_DIR = PROJECT_DIR / "assets/maps"
BUILD_DIR = PROJECT_DIR / "build"
PACK_MAP = PROJECT_DIR / "pack_map"

# Global state
loaded_map: Optional[MapFile] = None
current_map_file: Optional[str] = None

app = FastAPI(title="TrenchBroom MCP Server", version="1.0.0")


class MapEditor:
    """Map editing operations"""

    @staticmethod
    def load_map(map_file: str) -> Dict[str, Any]:
        """Load a .map file from the maps directory"""
        global loaded_map, current_map_file

        map_path = MAPS_DIR / map_file
        if not map_path.exists():
            return {"success": False, "error": f"Map file not found: {map_file}"}

        try:
            loaded_map = parse_map_file(str(map_path))
            current_map_file = map_file

            # Gather info
            entities = []
            for i, entity in enumerate(loaded_map.entities):
                origin = entity.origin
                entities.append(
                    {
                        "index": i,
                        "classname": entity.classname,
                        "origin": origin.to_list() if origin else None,
                        "brush_count": len(entity.brushes),
                        "properties": {
                            k: v
                            for k, v in entity.properties.items()
                            if k != "classname"
                        },
                    }
                )

            return {
                "success": True,
                "map_file": map_file,
                "entity_count": len(loaded_map.entities),
                "brush_count": loaded_map.brush_count(),
                "entities": entities,
            }

        except ParseError as e:
            return {"success": False, "error": f"Parse error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error loading map: {str(e)}"}

    @staticmethod
    def get_map_info() -> Dict[str, Any]:
        """Get detailed information about the currently loaded map"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        # Collect entity info
        entities = []
        textures = set()

        for i, entity in enumerate(loaded_map.entities):
            origin = entity.origin
            brushes_info = []

            for j, brush in enumerate(entity.brushes):
                brush_bounds = brush.bounds()
                brushes_info.append(
                    {
                        "index": j,
                        "face_count": len(brush.faces),
                        "center": brush.center().to_list(),
                        "bounds": {
                            "min": brush_bounds[0].to_list(),
                            "max": brush_bounds[1].to_list(),
                        }
                        if brush_bounds
                        else None,
                    }
                )

                # Collect textures
                for face in brush.faces:
                    textures.add(face.texture)

            entities.append(
                {
                    "index": i,
                    "classname": entity.classname,
                    "origin": origin.to_list() if origin else None,
                    "brush_count": len(entity.brushes),
                    "brushes": brushes_info,
                    "properties": {
                        k: v for k, v in entity.properties.items() if k != "classname"
                    },
                }
            )

        return {
            "success": True,
            "map_file": current_map_file,
            "entity_count": len(loaded_map.entities),
            "brush_count": loaded_map.brush_count(),
            "entities": entities,
            "textures": sorted(list(textures)),
        }

    @staticmethod
    def add_entity(
        classname: str, origin: List[float], properties: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Add a new entity to the map"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        try:
            entity = Entity(classname=classname)

            # Set origin
            if len(origin) >= 3:
                entity.origin = Vec3(origin[0], origin[1], origin[2])

            # Add custom properties
            if properties:
                for key, value in properties.items():
                    if key != "classname":  # Already set
                        entity.set_property(key, value)

            index = loaded_map.add_entity(entity)

            return {
                "success": True,
                "entity_index": index,
                "classname": classname,
                "origin": entity.origin.to_list() if entity.origin else None,
            }

        except Exception as e:
            return {"success": False, "error": f"Error adding entity: {str(e)}"}

    @staticmethod
    def move_entity(entity_id: int, origin: List[float]) -> Dict[str, Any]:
        """Move an entity to a new position"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        entity = loaded_map.get_entity_at_index(entity_id)
        if entity is None:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        try:
            old_origin = entity.origin

            if len(origin) >= 3:
                new_origin = Vec3(origin[0], origin[1], origin[2])
                entity.move_to(new_origin)

            return {
                "success": True,
                "entity_id": entity_id,
                "classname": entity.classname,
                "old_origin": old_origin.to_list() if old_origin else None,
                "new_origin": entity.origin.to_list() if entity.origin else None,
            }

        except Exception as e:
            return {"success": False, "error": f"Error moving entity: {str(e)}"}

    @staticmethod
    def move_brush(
        entity_id: int, brush_index: int, offset: List[float]
    ) -> Dict[str, Any]:
        """Move a brush within an entity by an offset"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        entity = loaded_map.get_entity_at_index(entity_id)
        if entity is None:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        if brush_index < 0 or brush_index >= len(entity.brushes):
            return {
                "success": False,
                "error": f"Brush {brush_index} not found in entity {entity_id}",
            }

        try:
            brush = entity.brushes[brush_index]
            old_center = brush.center()

            if len(offset) >= 3:
                offset_vec = Vec3(offset[0], offset[1], offset[2])
                brush.move(offset_vec)

            return {
                "success": True,
                "entity_id": entity_id,
                "brush_index": brush_index,
                "old_center": old_center.to_list(),
                "new_center": brush.center().to_list(),
            }

        except Exception as e:
            return {"success": False, "error": f"Error moving brush: {str(e)}"}

    @staticmethod
    def save_map(map_file: str = None) -> Dict[str, Any]:
        """Save the current map to file"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        target_file = map_file or current_map_file
        if not target_file:
            return {"success": False, "error": "No map file specified"}

        try:
            map_path = MAPS_DIR / target_file
            write_map(loaded_map, str(map_path))

            return {
                "success": True,
                "map_file": target_file,
                "entity_count": len(loaded_map.entities),
                "brush_count": loaded_map.brush_count(),
                "message": f"Map saved to {map_path}",
            }

        except Exception as e:
            return {"success": False, "error": f"Error saving map: {str(e)}"}

    @staticmethod
    def compile_map() -> Dict[str, Any]:
        """Compile the current map using pack_map"""
        global current_map_file

        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        if not current_map_file:
            return {"success": False, "error": "No map file specified"}

        # Ensure map is saved first
        save_result = MapEditor.save_map()
        if not save_result["success"]:
            return save_result

        try:
            # Create build directory if needed
            BUILD_DIR.mkdir(parents=True, exist_ok=True)

            # Compile using pack_map
            map_path = MAPS_DIR / current_map_file
            plb_name = current_map_file.replace(".map", ".plb")
            plb_path = BUILD_DIR / plb_name

            result = subprocess.run(
                [str(PACK_MAP), str(map_path), str(plb_path)],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_DIR),
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "map_file": current_map_file,
                    "plb_file": str(plb_path),
                    "message": f"Compiled successfully: {plb_path}",
                    "stdout": result.stdout if result.stdout else None,
                }
            else:
                return {
                    "success": False,
                    "error": f"Compilation failed",
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                }

        except Exception as e:
            return {"success": False, "error": f"Error compiling map: {str(e)}"}

    @staticmethod
    def get_geometry_at_point(
        position: List[float], radius: float = 32.0
    ) -> Dict[str, Any]:
        """Find entities and brushes near a point"""
        if loaded_map is None:
            return {"success": False, "error": "No map loaded"}

        if len(position) < 3:
            return {
                "success": False,
                "error": "Position must have 3 coordinates [x, y, z]",
            }

        try:
            point = Vec3(position[0], position[1], position[2])

            nearby_entities = []
            nearby_brushes = []

            for entity in loaded_map.entities:
                origin = entity.origin
                if origin:
                    dist = point.distance(origin)
                    if dist <= radius:
                        nearby_entities.append(
                            {
                                "index": loaded_map.entities.index(entity),
                                "classname": entity.classname,
                                "distance": dist,
                                "origin": origin.to_list(),
                            }
                        )

                # Check brush centers
                for i, brush in enumerate(entity.brushes):
                    center = brush.center()
                    dist = point.distance(center)
                    if dist <= radius:
                        bounds = brush.bounds()
                        nearby_brushes.append(
                            {
                                "entity_index": loaded_map.entities.index(entity),
                                "brush_index": i,
                                "entity_classname": entity.classname,
                                "distance": dist,
                                "center": center.to_list(),
                                "bounds": {
                                    "min": bounds[0].to_list(),
                                    "max": bounds[1].to_list(),
                                }
                                if bounds
                                else None,
                            }
                        )

            # Sort by distance
            nearby_entities.sort(key=lambda x: x["distance"])
            nearby_brushes.sort(key=lambda x: x["distance"])

            return {
                "success": True,
                "position": position,
                "radius": radius,
                "entity_count": len(nearby_entities),
                "brush_count": len(nearby_brushes),
                "entities": nearby_entities,
                "brushes": nearby_brushes,
            }

        except Exception as e:
            return {"success": False, "error": f"Error getting geometry: {str(e)}"}


class TrenchBroomLauncher:
    """Launch and control TrenchBroom map editor"""

    @staticmethod
    def launch(map_file: Optional[str] = None) -> Dict[str, Any]:
        """Launch TrenchBroom with optional map file"""
        try:
            # TrenchBroom executable path
            trenchbroom_path = (
                "/Applications/TrenchBroom.app/Contents/MacOS/TrenchBroom"
            )

            # Build command
            cmd = [trenchbroom_path]
            if map_file:
                map_path = str(MAPS_DIR / map_file)
                if not Path(map_path).exists():
                    return {
                        "success": False,
                        "error": f"Map file not found: {map_file}",
                    }
                cmd.append(map_path)

            # Launch TrenchBroom
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            return {
                "success": True,
                "message": f"TrenchBroom launched"
                + (f" with {map_file}" if map_file else ""),
                "map_file": map_file,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to launch TrenchBroom: {str(e)}",
            }


# MCP Tools Definition
MCP_TOOLS = {
    "load_map": {
        "name": "load_map",
        "description": "Load a Quake .map file from the assets/maps directory",
        "parameters": {
            "map_file": {
                "type": "string",
                "description": "Name of the map file (e.g., 'm1.map')",
                "required": True,
            }
        },
    },
    "get_map_info": {
        "name": "get_map_info",
        "description": "Get detailed information about the currently loaded map including all entities, brushes, and textures",
        "parameters": {},
    },
    "add_entity": {
        "name": "add_entity",
        "description": "Add a new entity to the map",
        "parameters": {
            "classname": {
                "type": "string",
                "description": "Entity class name (e.g., 'pickup_health', 'enemy_grunt')",
                "required": True,
            },
            "origin": {
                "type": "array",
                "description": "Position as [x, y, z]",
                "required": True,
            },
            "properties": {
                "type": "object",
                "description": "Additional entity properties",
                "required": False,
            },
        },
    },
    "move_entity": {
        "name": "move_entity",
        "description": "Move an entity to a new position",
        "parameters": {
            "entity_id": {
                "type": "integer",
                "description": "Entity index",
                "required": True,
            },
            "origin": {
                "type": "array",
                "description": "New position as [x, y, z]",
                "required": True,
            },
        },
    },
    "move_brush": {
        "name": "move_brush",
        "description": "Move a brush within an entity by an offset",
        "parameters": {
            "entity_id": {
                "type": "integer",
                "description": "Entity index",
                "required": True,
            },
            "brush_index": {
                "type": "integer",
                "description": "Brush index within the entity",
                "required": True,
            },
            "offset": {
                "type": "array",
                "description": "Offset as [x, y, z]",
                "required": True,
            },
        },
    },
    "save_map": {
        "name": "save_map",
        "description": "Save the current map to file",
        "parameters": {
            "map_file": {
                "type": "string",
                "description": "Map file name (optional, defaults to current loaded file)",
                "required": False,
            }
        },
    },
    "compile_map": {
        "name": "compile_map",
        "description": "Compile the current map using pack_map to generate .plb binary",
        "parameters": {},
    },
    "get_geometry_at_point": {
        "name": "get_geometry_at_point",
        "description": "Find entities and brushes near a specific point",
        "parameters": {
            "position": {
                "type": "array",
                "description": "Position as [x, y, z]",
                "required": True,
            },
            "radius": {
                "type": "number",
                "description": "Search radius (default 32)",
                "required": False,
            },
        },
    },
    "launch_trenchbroom": {
        "name": "launch_trenchbroom",
        "description": "Launch TrenchBroom map editor with optional map file",
        "parameters": {
            "map_file": {
                "type": "string",
                "description": "Optional map file to open (e.g., 'm1.map')",
                "required": False,
            }
        },
    },
}


# Tool dispatch
async def dispatch_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch tool call to appropriate handler"""

    if tool_name == "load_map":
        return MapEditor.load_map(parameters.get("map_file"))

    elif tool_name == "get_map_info":
        return MapEditor.get_map_info()

    elif tool_name == "add_entity":
        return MapEditor.add_entity(
            parameters.get("classname"),
            parameters.get("origin", []),
            parameters.get("properties"),
        )

    elif tool_name == "move_entity":
        return MapEditor.move_entity(
            parameters.get("entity_id"), parameters.get("origin", [])
        )

    elif tool_name == "move_brush":
        return MapEditor.move_brush(
            parameters.get("entity_id"),
            parameters.get("brush_index"),
            parameters.get("offset", []),
        )

    elif tool_name == "save_map":
        return MapEditor.save_map(parameters.get("map_file"))

    elif tool_name == "compile_map":
        return MapEditor.compile_map()

    elif tool_name == "get_geometry_at_point":
        return MapEditor.get_geometry_at_point(
            parameters.get("position", []), parameters.get("radius", 32.0)
        )

    elif tool_name == "launch_trenchbroom":
        return TrenchBroomLauncher.launch(parameters.get("map_file"))

    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


# MCP SSE endpoint
async def mcp_event_generator(request: Request):
    """Generate SSE events for MCP protocol"""

    # Send tools/list event
    tools_event = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {"tools": list(MCP_TOOLS.values())},
    }
    yield {"event": "tools/list", "data": json.dumps(tools_event)}

    # Keep connection alive with ping
    while True:
        if await request.is_disconnected():
            break

        yield {
            "event": "ping",
            "data": json.dumps({"timestamp": datetime.now().isoformat()}),
        }

        await asyncio.sleep(30)  # Ping every 30 seconds


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol"""
    return EventSourceResponse(mcp_event_generator(request))


@app.post("/invoke")
async def invoke_tool(request: Request):
    """Invoke an MCP tool"""
    try:
        body = await request.json()
        tool_name = body.get("tool")
        parameters = body.get("parameters", {})

        result = await dispatch_tool(tool_name, parameters)

        return JSONResponse({"jsonrpc": "2.0", "result": result})

    except Exception as e:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            },
            status_code=500,
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "loaded_map": current_map_file,
        "map_entity_count": len(loaded_map.entities) if loaded_map else 0,
    }


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {"tools": list(MCP_TOOLS.values())}


if __name__ == "__main__":
    print("Starting TrenchBroom MCP Server on http://127.0.0.1:9875")
    print(f"Project directory: {PROJECT_DIR}")
    print(f"Maps directory: {MAPS_DIR}")
    print(f"Pack map compiler: {PACK_MAP}")

    uvicorn.run(app, host="127.0.0.1", port=9875)
