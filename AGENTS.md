# Q1K3 - AGENTS.md

**The Definitive Guide for AI Agents and Developers Working on the Q1K3 Codebase**

---

## 1. Executive Summary

Q1K3 is a Quake-inspired 3D first-person shooter originally created for the JS13k 2021 competition. Now maintained as a modern static web application, it preserves the competition's efficiency ethos while remaining flexible for ongoing development:

**Key Question**: How should we frame the project's current state?

**Option A**: Keep it as "originally for JS13k, now general purpose"
**Option B**: Position as "efficiency-first game engine" 
**Option C**: Frame as "retro game preservation project"
**Option D**: Present as "educational reference implementation"

Please let me know your preference, and I'll use:

**Option A** - Originally for JS13k, now general purpose (keeping competition heritage visible)

Q1K3 features:

- **2 fully playable levels** with TrenchBroom map editing
- **5 enemy types** with AI (line-of-sight, no pathfinding)
- **3 weapons** (Shotgun, Nailgun, Grenade Launcher)
- **WebGL rendering** with dynamic lighting (up to 64 lights)
- **Spatial audio** with stereo separation and distance falloff
- **Entity-component architecture** with 25+ entity types
- **Zero external dependencies** at runtime

**Efficiency Philosophy**: Code remains optimized for small size and performance. Short variable names (`_a`, `_b`), dead code elimination, and compression-friendly patterns are encouraged but not mandatory. The focus is on clean, efficient code rather than extreme minification.

**Build System**: The `build.sh` script is maintained for **map and model compilation only** - generating binary level data (.plb) and model data (.rmf) from source assets. The JavaScript source files are loaded directly without minification for development and deployment.

---

## 2. Project Context

### JS13k Competition Constraints
- **13KB limit** for ZIP file (game.zip) - *Historical constraint, no longer mandatory*
- **No external dependencies** (everything must be self-contained)
- **Browser-based** (JavaScript + WebGL)
- **Competition deadline** typically in September

### Why This Architecture?
- **Multiple source files** → Easier development, merged by build script (optional for modern deployment)
- **Custom binary formats** (.plb, .rmf) → Smaller than JSON/text
- **Procedural textures** (TTT) → No image assets to download
- **Synthesized audio** (Sonant-X fork) → No audio files
- **C map compiler** → Complex CSG operations at build time (optional)

### Reference Materials
- **Play**: https://phoboslab.org/q1k3/
- **Making Of**: https://phoboslab.org/log/2021/09/q1k3-making-of
- **JS13k Rules**: https://js13kgames.com/#rules

---

## 3. Architecture Overview

### System Architecture (Text Diagram)

```
┌─────────────────────────────────────────────────────────────────┐
│                           GAME LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   game.js   │  │  weapons.js │  │   input.js  │             │
│  │ (game loop) │  │  (weapon    │  │ (controls)  │             │
│  │ (spawning)  │  │   system)   │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ENTITY SYSTEM                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐│
│  │entity_t     │  │entity_player│  │ entity_enemy│  │entity_pick││
│  │(base class) │  │     _t      │  │    _t      │  │   up_t    ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘│
│       │                  │               │               │      │
│       └──────────────────┴───────────────┴───────────────┘      │
│                           entity_*.js files (25 types)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RENDERING PIPELINE                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ renderer.js │  │   model.js  │  │   map.js    │             │
│  │ (WebGL ctx) │  │ (.rmf loader│  │(.plb loader │             │
│  │ (shaders)   │  │  geometry)  │  │  collision) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ASSET PIPELINE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │textures.js  │  │   ttt.js    │  │  audio.js   │             │
│  │(data only)  │  │(procedural │  │(Sonant-X   │             │
│  │             │  │  generator)│  │   synth)    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Entity-Component Hybrid**: Base `entity_t` class with inheritance for specialized types
2. **Binary Asset Formats**: Custom .plb (maps) and .rmf (models) for size efficiency
3. **Deferred Rendering**: All draw calls collected, lights batched, drawn once per frame
4. **Object Pooling**: Particles and gibs reuse model pieces
5. **Global Scope Usage**: Strategic globals for size (`r_camera`, `game_time`, `gl` shorthand)

---

## 4. Development Guidelines

### Code Style Rules

**ALWAYS follow these conventions:**

```javascript
// 1. Short variable names (2-3 chars preferred)
let ff = Math.min(this.f * game_tick, 1);  // GOOD
let frictionFactor = Math.min(this.friction * game_tick, 1);  // BAD

// 2. Arrow functions
let clamp = (v, min, max) => v < min ? min : (v > max ? max : v);  // GOOD
function clamp(v, min, max) { return ... }  // BAD

// 3. Global declarations with single let
let
    game_tick = 0,
    game_time = 0.016;  // GOOD

let game_tick = 0;  // BAD (wastes bytes)
let game_time = 0.016;

// 4. DEBUG blocks for development-only code
/*DEBUG[*/ console.log('debug info'); /*]*/  // Preserved in development, remove manually for production

// 5. Underscore prefix for private/internal
this._health = 50;    // Internal property
this.p = pos;         // Public property (position)
```

### Entity Development Pattern

When creating a new entity type:

```javascript
// 1. Extend appropriate base class
class entity_mytype_t extends entity_enemy_t {
    // 2. Override _init for setup
    _init(custom_param) {
        super._init();  // Call parent if extending enemy/player
        
        this._model = model_whatever;   // Required for rendering
        this._texture = 5;               // Texture index
        this._health = 50;               // Health points
        this._check_against = ENTITY_GROUP_PLAYER;  // Collision target
        
        // Register in appropriate collision groups
        game_entities_enemies.push(this);
    }
    
    // 3. Override _update for behavior
    _update() {
        // Custom logic here
        this._update_physics();  // If needs physics
        this._draw_model();      // If has model
    }
    
    // 4. Optional: collision callbacks
    _did_collide(axis) {
        // axis: 0=x, 1=y, 2=z
    }
    
    _did_collide_with_entity(other) {
        // Called when colliding with _check_against group
    }
    
    // 5. Optional: custom death
    _kill() {
        super._kill();
        // Spawn particles, play sounds, etc.
    }
}
```

### Adding to Source Files

When adding new JavaScript files, update `index.html` to include them in the correct order:

```html
<!-- Example: adding a new entity type -->
<script type="text/javascript" src="source/entity_mytype.js"></script>
<!-- Must be loaded after entity.js and before game.js -->
```

**Loading Order Rule**: Files using globals from other files must be loaded AFTER those files. The current order in `index.html` is:

1. Core systems (math_utils.js, renderer.js, model.js, map.js)
2. Entity base class (entity.js)
3. Entity types (player, enemies, pickups, projectiles)
4. Game systems (weapons.js, game.js, main.js)

---

## 5. Build System Reference

### Purpose

The `build.sh` script exists solely for **asset compilation**:
- Converting TrenchBroom .map files → binary .plb format
- Converting Blender .obj files → binary .rmf format

**The JavaScript source files are NOT processed by the build system.** They are loaded directly via `index.html` in development and deployment.

### When You Need the Build System

**Required when**:
- Creating or modifying levels in TrenchBroom (generates new .map → needs .plb)
- Importing new 3D models from Blender (generates new .obj → needs .rmf)
- Adding new animation frames to existing models

**NOT required when**:
- Modifying JavaScript game logic
- Changing textures (textures.js is plain JS)
- Changing audio (sounds are generated in main.js)
- UI tweaks, bug fixes, gameplay adjustments

### Asset Pipeline (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASSET COMPILATION ONLY                         │
└─────────────────────────────────────────────────────────────────┘

TrenchBroom .map files
     │
     ▼
┌─────────────┐    pack_map.c (C compiler)
│  .map       │ ───────────────────────────►  .plb (binary level data)
│(brushes,    │    CSG operations, collision
│ entities)   │    map generation
└─────────────┘

Blender .obj files
     │
     ▼
┌─────────────┐    pack_model.php (PHP)
│  .obj       │ ───────────────────────────►  .rmf (binary model data)
│(vertices,   │    Vertex normalization,
│  faces)     │    animation frame packing
└─────────────┘
```

### Build Commands

**Prerequisites**:
- GCC or Clang (for pack_map.c)
- PHP 7.0+ (for pack_model.php)

**Compile the map compiler** (one-time setup):
```bash
gcc -std=c99 pack_map.c -lm -o pack_map
```

**Compile a single map**:
```bash
./pack_map assets/maps/m1.map build/m1.plb
```

**Compile all maps** (as defined in build.sh):
```bash
# Build both maps
./pack_map assets/maps/m1.map build/m1.plb
./pack_map assets/maps/m2.map build/m2.plb

# Concatenate into single file
cat build/m1.plb build/m2.plb > build/l
```

**Compile models**:
```bash
# Single model (static)
php pack_model.php assets/models/box.obj build/box.rmf

# Animated model (multiple frames)
php pack_model.php \
    assets/models/unit_idle.obj \
    assets/models/unit_run_1.obj \
    assets/models/unit_run_2.obj \
    build/unit.rmf

# Concatenate all models
cat build/*.rmf > build/m
```

**Run full asset build**:
```bash
./build.sh
```

### Dependency Loading Order (Critical!)

For development, files are loaded in `index.html` in this exact order:

```html
<script src="source/wrap_pre.js"></script>     <!-- Global wrapper start -->
<script src="source/document.js"></script>   <!-- DOM injection -->
<script src="source/textures.js"></script>   <!-- TTT texture data -->
<script src="source/music.js"></script>       <!-- Music data -->
<script src="source/audio.js"></script>       <!-- Audio synthesizer -->
<script src="source/input.js"></script>      <!-- Input handling -->
<script src="source/ttt.js"></script>        <!-- Texture generator -->
<script src="source/math_utils.js"></script>  <!-- Math functions -->
<script src="source/renderer.js"></script>    <!-- WebGL abstraction -->
<script src="source/model.js"></script>       <!-- .rmf loader -->
<script src="source/map.js"></script>        <!-- .plb loader + collision -->
<script src="source/entity.js"></script>      <!-- Base entity class -->
<script src="source/entity_player.js"></script>
<script src="source/entity_door.js"></script>
<script src="source/entity_light.js"></script>
<script src="source/entity_torch.js"></script>
<script src="source/entity_barrel.js"></script>
<script src="source/entity_particle.js"></script>
<!-- ... more entity files ... -->
<script src="source/weapons.js"></script>
<script src="source/game.js"></script>
<script src="source/main.js"></script>
<script src="source/wrap_post.js"></script>  <!-- Global wrapper end -->
```

**Rule**: Files using globals from other files must come AFTER those files.

---

## 6. Testing Procedures

### Manual Testing Checklist

```markdown
□ Game loads without console errors
□ Title screen displays "Q1K3 - CLICK TO START"
□ Click starts game, music plays
□ WASD movement works
□ Mouse look works (horizontal and vertical)
□ Weapon switching (Q/E or scroll) works
□ Shooting (click) works for all weapons
□ Enemies spawn and move toward player
□ Enemy projectiles damage player
□ Player projectiles damage enemies
□ Pickups (health, ammo, weapons) can be collected
□ Level transition triggers work
□ Second level loads correctly
□ "THE END" screen displays after level 2
□ Player death and respawn works
□ Fullscreen button works
□ Mouse sensitivity slider works
```

### Asset Build Verification

After running the build script for map/model compilation, verify the binary files were created:

```bash
# Check that map data file exists and has content
ls -la build/l

# Check that model data file exists and has content  
ls -la build/m

# Verify the game loads correctly in browser
# Open index.html and check console for any loading errors
```

### Size Monitoring (Optional)

While the 13KB limit is no longer mandatory, maintaining awareness of bundle size is still valuable:

```bash
# Check total JavaScript size
find source -name "*.js" -exec cat {} \; | wc -c

# Check individual large files (if any exceed 50KB, consider splitting)
wc -c source/*.js | sort -n
```

The original build pipeline with full minification and compression is available in the git history if needed for reference or educational purposes.

### When To Optimize

While the strict 13KB limit is no longer enforced, consider these optimizations for performance or if you want to maintain the efficient codebase:

**Performance optimizations** (apply when experiencing lag):
1. **Reduce particle counts** - Lower spawn amounts in entity files
2. **Reduce active lights** - Limit dynamic lights in renderer.js
3. **Simplify collision checks** - Optimize entity collision logic
4. **Reduce texture resolution** - Use smaller TTT texture sizes

**Code size optimizations** (apply if bundle becomes unreasonably large):
1. **Remove unused textures** (textures.js) - Delete unused texture definitions
2. **Simplify enemy types** - Remove specialized enemies, use base enemy
3. **Reduce sound variety** - Comment out in main.js audio generation
4. **Remove unused weapons** - Comment out in weapons.js and main.js
5. **Simplify geometry** - Reduce faces in .obj models
6. **Remove levels** - Build with only m1.map for smaller deployment

---

## 7. Entity System Catalog

### Base Classes

| File | Class | Purpose | Key Properties |
|------|-------|---------|----------------|
| `entity.js` | `entity_t` | Base for all entities | `p` (pos), `v` (vel), `a` (accel), `_health`, `_dead`, `_model`, `_texture` |
| `entity_enemy.js` | `entity_enemy_t` | AI enemies | `_STATE_*`, `_ANIMS[]`, `_attack_distance`, `_speed` |
| `entity_pickup.js` | `entity_pickup_t` | Collectibles | Auto-collect when near player |

### Complete Entity List

```
ENTITY HIERARCHY
│
├── entity_player_t (entity_player.js)
│   └── Player controller, camera, weapons
│
├── entity_enemy_t (entity_enemy.js)
│   ├── entity_enemy_grunt_t (entity_enemy_grunt.js)
│   ├── entity_enemy_enforcer_t (entity_enemy_enforcer.js)
│   ├── entity_enemy_ogre_t (entity_enemy_ogre.js)
│   ├── entity_enemy_zombie_t (entity_enemy_zombie.js)
│   └── entity_enemy_hound_t (entity_enemy_hound.js)
│
├── entity_pickup_t (entity_pickup.js)
│   ├── entity_pickup_nailgun_t
│   ├── entity_pickup_grenadelauncher_t
│   ├── entity_pickup_health_t
│   ├── entity_pickup_nails_t
│   ├── entity_pickup_grenades_t
│   └── entity_pickup_key_t
│
├── entity_projectile_* (6 files)
│   ├── entity_projectile_nail_t
│   ├── entity_projectile_grenade_t
│   ├── entity_projectile_shell_t
│   ├── entity_projectile_plasma_t
│   └── entity_projectile_gib_t
│
├── entity_particle_t (entity_particle.js)
├── entity_light_t (entity_light.js)
├── entity_torch_t (entity_torch.js)
├── entity_barrel_t (entity_barrel.js)
├── entity_door_t (entity_door.js)
└── entity_trigger_level_t (entity_trigger_level.js)
```

### Entity Group System

Collision groups defined in `entity.js`:

```javascript
ENTITY_GROUP_NONE = 0      // Collides with nothing
ENTITY_GROUP_PLAYER = 1    // Player entities
ENTITY_GROUP_ENEMY = 2     // Enemies and obstacles

// Usage:
this._check_against = ENTITY_GROUP_PLAYER;  // This entity checks collisions with players
```

### Entity Lifecycle

```javascript
// 1. Spawn
game_spawn(entity_type_t, position, param1, param2);

// 2. Constructor calls _init()
constructor(pos, p1, p2) {
    this._init(p1, p2);
}

// 3. Update loop (every frame)
_update() {
    this._update_physics();  // If uses physics
    this._draw_model();      // If has model
}

// 4. Death
_kill() {
    this._dead = 1;  // Removed from game_entities next frame
}
```

---

## 8. Asset Pipeline Guide

### Map Creation (TrenchBroom → .plb)

**Tools Required**: TrenchBroom (https://trenchbroom.github.io/)

**Entity Classes** (must match pack_map.c lines 971-1051):
```
info_player_start        → type 0  (player spawn)
enemy_grunt              → type 1  (basic enemy)
enemy_enforcer           → type 2  (tougher enemy)
enemy_ogre               → type 3  (heavy enemy)
enemy_zombie             → type 4  (fast enemy)
enemy_hound              → type 5  (dog enemy)
pickup_nailgun           → type 6
pickup_grenadelauncher   → type 7
pickup_health            → type 8
pickup_nails             → type 9
pickup_grenades          → type 10
barrel                   → type 11
light                    → type 12  (extra: light=N, color="R G B")
trigger_levelchange      → type 13
door                     → type 14  (extra: texture=N, dir=N)
pickup_key               → type 15
torch                    → type 16
```

**Map Constraints**:
- Block resolution: X/Z = 32 units, Y = 16 units
- Max position: X/Z = 8192 (256*32), Y = 4096 (256*16)
- Min brush size: 32×16×32
- Texture names must be numbers: "0", "1", "5.png"

**Build Command**:
```bash
./pack_map assets/maps/my_level.map build/my_level.plb
```

### Model Creation (Blender → .rmf)

**Constraints**:
- Max 127 vertices per frame
- Max 127 faces (indices)
- Vertices normalized to (-15, 15) range
- Frames share same topology (vertex indices)

**Animation**: Export separate .obj files:
```
unit_idle.obj     → frame 0 (static)
unit_run_1.obj    → frame 1
unit_run_2.obj    → frame 2
...
```

**Build Command**:
```bash
php pack_model.php \
    assets/models/unit_idle.obj \
    assets/models/unit_run_1.obj \
    assets/models/unit_run_2.obj \
    build/unit.rmf
```

### Texture Generation (TTT)

Textures defined in `textures.js` as arrays:

```javascript
// Format: [width, height, bg_color, commands...]
[64, 64, 0x38751,  // width, height, background (RGBA4444)
    1, 0, 2, 10, 2, 11, 4, 65528,  // cmd 1: rectangle_multiple
    10, 25931, 
    4, 0, 0, 0, 64, 64, 14  // cmd 4: draw texture index 14
]
```

**TTT Commands** (from ttt.js):
- `0` - Rectangle: x, y, w, h, top_color, bottom_color, fill_color
- `1` - Rectangle multiple: start_x, start_y, w, h, inc_x, inc_y, colors...
- `2` - Random noise: color, size
- `3` - Text: x, y, color, font(0=sans,1=serif), size, text
- `4` - Draw previous texture: index, x, y, w, h, alpha

### Audio Creation (Sonant-X)

Music in `music.js`, sounds generated in `main.js`:

```javascript
// Sound format: 28-value array
[   // Index: property
    8,  // 0: osc1_oct
    0,  // 1: osc1_det
    0,  // 2: osc1_detune
    1,  // 3: osc1_xenv
    148,// 4: osc1_vol
    1,  // 5: osc1_waveform (0=sin,1=square,2=saw,3=tri)
    3,  // 6: osc2_oct
    5,  // 7: osc2_det
    0,  // 8: osc2_detune
    0,  // 9: osc2_xenv
    139,// 10: osc2_vol
    1,  // 11: osc2_waveform
    0,  // 12: noise_fader
    2653, // 13: env_attack
    0,  // 14: env_sustain
    2193, // 15: env_release
    255,// 16: master
    2,  // 17: fx_filter (0=none,1=high,2=low,3=band,4=notch)
    639,// 18: fx_freq
    119,// 19: fx_resonance
    2,  // 20: fx_delay_time
    23, // 21: fx_delay_amt
    0,  // 22: fx_pan_freq_p
    0,  // 23: fx_pan_amt
    0,  // 24: lfo_osc1_freq
    0,  // 25: lfo_fx_freq
    0,  // 26: lfo_freq_p
    0   // 27: lfo_amt
]

// Generate
sfx_shotgun_shoot = audio_create_sound(135, [...instrument_array]);
audio_play(sfx_shotgun_shoot);
```

---

## 9. Optimization Strategies

### Efficiency Guidelines

```markdown
□ Use 2-3 char variable names everywhere (maintain original style)
□ Arrow functions over function declarations
□ Single let/var declarations for multiple vars
□ No unnecessary comments
□ DEBUG[] blocks for dev-only code
□ Underscore prefix for private/internal (_property)
□ Avoid long property names
□ Template literals only when needed
□ No external libraries (keep self-contained philosophy)
□ Binary formats over JSON/text (for assets)
□ Reuse code patterns (consistent style)
```

### Performance Optimization Patterns

**Object Pooling** (see entity_particle.js, entity.js `_spawn_particles`):
```javascript
// Don't create new objects per frame - reuse
// Particles are spawned but not stored; they auto-cleanup
```

**Early Exit Rendering** (renderer.js):
```javascript
// Lights fade out by distance before being added
let fade = clamp(scale(vec3_dist(pos, r_camera), 768, 1024, 1, 0), 0, 1);
if (fade && r_num_lights < R_MAX_LIGHT_V3/2) {
    r_light_buffer.set([...], r_num_lights*6);
    r_num_lights++;
}
```

**WebGL State Minimization** (renderer.js):
```javascript
// Batch draw calls by texture
let last_texture = -1;
for (let c of r_draw_calls) {
    if (last_texture != c[5]) {
        last_texture = c[5];
        gl.bindTexture(gl.TEXTURE_2D, r_textures[last_texture].t);
    }
    gl.drawArrays(gl.TRIANGLES, c[6], c[9]);
}
```

**Physics Sub-Stepping** (entity.js):
```javascript
// Fast objects don't tunnel through walls
let steps = Math.ceil(vec3_length(move_dist) / 16);
for (let s = 0; s < steps; s++) {
    // Move in small increments
}
```

### Compression-Friendly Code

```javascript
// GOOD: Patterns repeat, compresses well
let a = vec3(0, 0, 0);
let b = vec3(1, 1, 1);
let c = vec3(2, 2, 2);

// BAD: Unique patterns everywhere
let playerPosition = vec3(0, 0, 0);
let enemyPosition = vec3(1, 1, 1);
let pickupPosition = vec3(2, 2, 2);

// GOOD: Consistent structure
class entity_t {
    _init() {}
    _update() {}
    _kill() {}
}

class entity_a_t extends entity_t {
    _init() { super._init(); }
}

// GOOD: Reuse variable names across scope
function foo() {
    let a = 1;
    return a;
}
function bar() {
    let a = 2;
    return a;
}
```

---

## 10. Troubleshooting

### Common Build Failures

**Problem**: `pack_map.c` compilation fails
```bash
# Solution: Install gcc and math library
gcc -std=c99 pack_map.c -lm -o pack_map
# On macOS: clang works too
```

**Problem**: PHP packer scripts fail
```bash
# Solution: Ensure PHP 7.0+ installed
php --version
# Check file paths in build.sh are correct
```

### Debug Mode

Enable debug info in development:
```javascript
// In source files, use DEBUG blocks
/*DEBUG[*/ console.log('Entity spawned:', this); /*]*/

// DEBUG blocks are preserved in development via index.html
// They can be manually removed for production if desired
```
// $js = preg_replace('/\/\*DEBUG\[.*?\/\*\]\*\//sm', '', $js);
```

For development, use `index.html` which loads unminified sources separately.

### Browser DevTools Tips

1. **Unminified debugging**: Use `index.html` during development
2. **Compressed debugging**: Add source map (costs ~500 bytes, usually not worth it)
3. **Entity inspection**: Add `window.e = game_entities;` in console to inspect
4. **Performance profiling**: Use Chrome DevTools Performance tab, look for:
   - GC pauses (reduce allocations)
   - Long frames (reduce entity count or draw calls)
   - Shader compilation time (happens once at init)

---

## 11. Glossary

| Term | Definition |
|------|------------|
| **.plb** | Packed Level Binary - custom map format |
| **.rmf** | Retarded Model Format - custom model format |
| **TTT** | Tiny Texture Tumbler - procedural texture generator |
| **Sonant-X** | JavaScript audio synthesizer (heavily modified) |
| **Roadroller** | Advanced JS compressor using statistical modeling |
| **advzip** | ZIP recompressor (part of advancecomp) |
| **CSG** | Constructive Solid Geometry - brush-based level editing |
| **Entity** | Game object (player, enemy, pickup, etc.) |
| **Group** | Collision category (player, enemy, none) |
| **Frame Mix** | Vertex interpolation between animation frames |
| **WebGL Shorthand** | gl.createProgram() → gl.crP() (size optimization) |
| **DEBUG[]** | Comment pattern for development-only code |
| **UglifyJS** | JavaScript minifier and compressor |
| **TrenchBroom** | Quake-style level editor |

---

## 12. Emergency Procedures

### Critical Bug Fix Protocol

1. **Isolate issue**: Test in unminified version (`index.html`)
2. **Fix in source**: Edit appropriate `source/entity_*.js` file
3. **Test fix**: Open `index.html` in browser, verify
4. **Document**: Add comment explaining fix

### Adding New Features Safely

```markdown
1. □ Implement in source/
2. □ Test with index.html
3. □ Add to build.sh if new file (only for map/model compilation)
4. □ Verify game still completes both levels
5. □ Verify no console errors
6. □ Verify enemies still work
7. □ Verify weapons still work
8. □ Verify pickups still work
```

---

## Document History

- **Created**: 2026-02-26
- **Based on**: Q1K3 JS13k 2021 entry analysis
- **Author**: AI Agent conducting comprehensive codebase analysis
- **Version**: 1.0 (Initial comprehensive documentation)

---

**End of AGENTS.md**


## Appendix A: Pre-Flight Checklist

**Use this checklist before starting major changes to the Q1K3 codebase.**

### ✅ System Prerequisites

**Required Software:**
- **macOS** (tested on macOS 15+)
- **Homebrew** (`brew --version`)
- **Git** (pre-installed on macOS)
- **PHP 8.2+** (`php --version`)
- **GCC/Clang** (`gcc --version` - for compiling pack_map.c)

**Quick Verification:**
```bash
brew --version && php --version && gcc --version
```

### ✅ Project Setup

**Build Tools:**
- [ ] **pack_map compiled** (`ls -la pack_map` shows executable)
- [ ] **Maps compiled** (`ls -lh build/l` exists and is > 4KB)
- [ ] **Build directory ready** (`ls build/` shows l, m1.plb, m2.plb)
- [ ] **fswatch installed** (`brew install fswatch` - for auto-compilation)

**Quick Setup:**
```bash
# Compile pack_map (one-time)
gcc -std=c99 pack_map.c -lm -o pack_map

# Compile maps
./pack_map assets/maps/m1.map build/m1.plb
./pack_map assets/maps/m2.map build/m2.plb
cat build/*.plb > build/l
```

### ✅ MCP Servers (Development Tools)

**Currently Working:**
- [ ] **Chrome DevTools MCP** - For browser testing (`opencode mcp list` shows ✓)
- [ ] **Blender MCP** - For 3D modeling (`opencode mcp list` shows ✓)
- [ ] **TrenchBroom MCP** - For map editing (via `./tb-mcp` wrapper)

**Verification:**
```bash
# Check all MCP servers
opencode mcp list

# Test TrenchBroom MCP
./tb-mcp status
./tb-mcp launch m1.map
```

### ✅ Testing Setup

**Browser Testing:**
- [ ] Open `index.html` in Chrome/Firefox
- [ ] WebGL enabled (check console for errors)
- [ ] Game loads without JavaScript errors
- [ ] Both levels (m1 and m2) load correctly

**MCP Tool Testing:**
```bash
# Test Chrome DevTools
opencode mcp list | grep chrome-devtools

# Test Blender (if using)
opencode mcp list | grep blender-mcp

# Test TrenchBroom
./tb-mcp info
```

### 🎯 Pre-Flight Verification Command

Run this single command to verify everything:

```bash
echo "=== Q1K3 Pre-Flight Check ===" && \
echo "1. Build tools:" && ls -lh pack_map build/l && \
echo "" && \
echo "2. MCP servers:" && \
opencode mcp list 2>&1 | grep -E "(chrome-devtools|blender)" && \
echo "" && \
echo "3. TrenchBroom MCP:" && \
./tb-mcp status && \
echo "" && \
echo "4. fswatch:" && which fswatch && \
echo "" && \
echo "✅ Ready for development!"
```

---

## Appendix B: Development Workflow

### Daily Development (No Build Needed!)

```bash
# Just edit and refresh!
edit source/entity_player.js
open index.html  # Refresh browser to see changes
```

### Level Editing (Build Required)

**Option 1: Auto-Compilation (Recommended)**
```bash
# Start the map watcher in a terminal window
./watch-maps.sh

# This will:
# - Watch assets/maps/*.map for changes
# - Auto-compile when you save in TrenchBroom
# - Update build/l automatically
# - Show success/error messages
```

**Option 2: Manual Workflow**
```bash
# When editing maps in TrenchBroom
./pack_map assets/maps/m1.map build/m1.plb
cat build/*.plb > build/l

# Refresh browser to see changes
```

### Model Import (Build Required)

```bash
# When adding models from Blender
php pack_model.php assets/models/my_model.obj build/my_model.rmf
cat build/*.rmf > build/m

# Refresh browser
```

---

## Appendix C: MCP Server Setup

### Blender MCP Server

The Blender MCP server enables AI-driven 3D modeling and scene manipulation directly from opencode using the official `blender-mcp` Python package.

**Prerequisites:**
- Blender 3.0+ installed
- Python 3.10+ installed
- [uv package manager](https://github.com/astral-sh/uv) installed: `brew install uv`

**Setup Steps:**

1. **Install the Blender MCP addon:**
   - Download `addon.py` from https://github.com/ahujasid/blender-mcp
   - In Blender: Edit → Preferences → Add-ons → Install → Select `addon.py`
   - Enable the addon by checking "Interface: Blender MCP"

2. **Start the MCP server in Blender:**
   - Press **N** in the 3D viewport to open the sidebar
   - Find the **"Blender MCP"** panel
   - Ensure port is set to `9876` (default)
   - Click **"Start Server"**
   - Should show "Running on port 9876"

3. **Verify in opencode:**
   ```bash
   opencode mcp list
   ```
   Should show: ✓ blender-mcp connected

**How it works:**
- The Blender addon runs a socket server on port 9876
- The `uvx blender-mcp` command starts a stdio-based MCP server that bridges to Blender
- opencode connects via stdio transport (more reliable than SSE)

**Troubleshooting:**

- If the server shows "failed" in opencode:
  - Check that Blender MCP panel shows "Running on port 9876"
  - Use `lsof -P -i :9876` to verify Blender is listening
  - Make sure `uvx` is installed: `which uvx`
- If you see "Connection refused" errors, the Blender addon isn't running
- Restart both Blender (with addon enabled) and opencode

### TrenchBroom MCP Server

The TrenchBroom MCP server enables AI-assisted Quake map editing for the Q1K3 project. The server runs as a LaunchAgent service and provides tools to edit maps and launch TrenchBroom.

**Setup:**
The TrenchBroom MCP server runs automatically via macOS LaunchAgent on port 9875. If not running:
```bash
launchctl load ~/Library/LaunchAgents/com.q1k3.trenchbroom-mcp.plist
```

Or start manually:
```bash
cd /Users/jtally/s1k3 && python3 tb_mcp_server.py &
```

**Available Tools:**
- `load_map` - Load a Quake .map file
- `get_map_info` - Get map details (entities, brushes, textures)
- `add_entity` - Add new entity to map
- `move_entity` - Move entity to new position
- `move_brush` - Move brush within entity
- `save_map` - Save map to file
- `compile_map` - Compile map to .plb binary
- `get_geometry_at_point` - Find geometry near position
- `launch_trenchbroom` - Launch TrenchBroom editor (optionally with map file)

**Example - Launch TrenchBroom via HTTP API:**
```bash
# Launch TrenchBroom without map
curl -s -X POST http://localhost:9875/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "launch_trenchbroom", "parameters": {}}'

# Launch TrenchBroom with specific map
curl -s -X POST http://localhost:9875/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "launch_trenchbroom", "parameters": {"map_file": "m1.map"}}'
```

**Verify:**
```bash
curl -s http://localhost:9875/sse | head -1
```
Should return: `event: tools/list`

**Easy-to-use Wrapper Script:**
A convenient bash wrapper script `tb-mcp` is provided for easier interaction:

```bash
# Check server status
./tb-mcp status

# Launch TrenchBroom
./tb-mcp launch              # Launch without map
./tb-mcp launch m1.map       # Launch with specific map

# Load and edit maps
./tb-mcp load m1.map         # Load a map
./tb-mcp info                # Show map information
./tb-mcp save                # Save current map
./tb-mcp compile             # Compile to .plb binary

# Edit entities
./tb-mcp add pickup_health 100 200 64                    # Add entity
./tb-mcp move 5 150 250 80                               # Move entity #5
./tb-mcp move-brush 3 0 10 0 0                           # Move brush
./tb-mcp find-at 500 500 500 64                          # Find geometry
```

Run `./tb-mcp help` for full usage information.

---

## Appendix D: Common Issues & Fixes

### "pack_map not found"
```bash
gcc -std=c99 pack_map.c -lm -o pack_map
```

### "TrenchBroom MCP server not running"
```bash
# Option 1: Start via LaunchAgent
launchctl load ~/Library/LaunchAgents/com.q1k3.trenchbroom-mcp.plist

# Option 2: Start manually
cd /Users/jtally/s1k3 && python3 tb_mcp_server.py &

# Verify it's running
./tb-mcp status
```

### "fswatch not found"
```bash
brew install fswatch
```

### "Maps not updating in browser"
```bash
# Make sure build/l exists and is up to date
ls -lh build/l

# Recompile if needed
./pack_map assets/maps/m1.map build/m1.plb
./pack_map assets/maps/m2.map build/m2.plb
cat build/*.plb > build/l
```

### "Blender MCP not connecting"
1. Make sure Blender is running
2. Check that Blender MCP addon shows "Running on port 9876"
3. Restart opencode if needed
4. Run `opencode mcp list` to verify


---

**End of AGENTS.md**

*This document is a living guide. Update it as the codebase evolves, especially when adding new entity types, changing the build pipeline, or discovering new optimization techniques.*
