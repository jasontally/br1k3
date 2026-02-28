#!/bin/bash
# Q1K3 Auto-Compile Watch Script
# Watches for changes in assets/maps/*.map and auto-compiles to build/

PROJECT_DIR="/Users/jtally/s1k3"
MAPS_DIR="$PROJECT_DIR/assets/maps"
BUILD_DIR="$PROJECT_DIR/build"
PACK_MAP="$PROJECT_DIR/pack_map"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Q1K3 Map Auto-Compile Watcher ===${NC}"
echo ""
echo "This script watches for changes in .map files and auto-compiles them."
echo ""
echo -e "${YELLOW}Requirements:${NC}"
echo "  - fswatch (install: brew install fswatch)"
echo "  - TrenchBroom saves .map files to: $MAPS_DIR"
echo ""

# Check for fswatch
if ! command -v fswatch &> /dev/null; then
    echo -e "${YELLOW}⚠️  fswatch not found. Installing...${NC}"
    brew install fswatch
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install fswatch. Please install manually: brew install fswatch"
        exit 1
    fi
fi

# Create build directory if needed
mkdir -p "$BUILD_DIR"

# Function to compile a single map
compile_map() {
    local map_file="$1"
    local map_name=$(basename "$map_file" .map)
    local plb_file="$BUILD_DIR/${map_name}.plb"
    
    echo -e "${BLUE}📝 Detected change: $map_name.map${NC}"
    echo -e "${YELLOW}⚙️  Compiling...${NC}"
    
    if "$PACK_MAP" "$map_file" "$plb_file"; then
        echo -e "${GREEN}✅ Compiled: $map_name.plb${NC}"
        
        # Concatenate all maps
        echo -e "${YELLOW}📦 Concatenating all maps...${NC}"
        cat "$BUILD_DIR"/*.plb > "$BUILD_DIR/l"
        echo -e "${GREEN}✅ Updated: build/l${NC}"
        
        # Show file sizes
        ls -lh "$BUILD_DIR"/l "$plb_file" 2>/dev/null | tail -2
        
        echo ""
        echo -e "${GREEN}🎮 Ready to test! Refresh your browser to see changes.${NC}"
        echo ""
    else
        echo -e "❌ Compilation failed for $map_name.map"
    fi
}

# Check initial state
echo -e "${BLUE}📊 Initial state:${NC}"
if ls "$MAPS_DIR"/*.map &>/dev/null; then
    echo "Found map files:"
    ls -lh "$MAPS_DIR"/*.map
else
    echo "⚠️  No .map files found in $MAPS_DIR"
    echo "   Create maps in TrenchBroom and save to this directory"
fi

echo ""

# Compile existing maps on startup
if ls "$MAPS_DIR"/*.map &>/dev/null; then
    echo -e "${YELLOW}⚙️  Compiling existing maps...${NC}"
    for map_file in "$MAPS_DIR"/*.map; do
        compile_map "$map_file"
    done
fi

echo ""
echo -e "${BLUE}👀 Watching for changes in: $MAPS_DIR${NC}"
echo -e "${BLUE}   Press Ctrl+C to stop${NC}"
echo ""

# Watch for changes
fswatch -o "$MAPS_DIR"/*.map 2>/dev/null | while read event; do
    # Get the most recently modified map file
    latest_map=$(ls -t "$MAPS_DIR"/*.map 2>/dev/null | head -1)
    if [ -n "$latest_map" ]; then
        compile_map "$latest_map"
    fi
done
