// Safe zone entity - shrinks over time, damages entities outside
// Center position and radius define the safe area

class entity_safe_zone_t extends entity_t {
	_init(start_radius, shrink_time) {
		this._center = vec3(this.p.x, 0, this.p.z);
		this._radius = start_radius || 2500;
		this._start_radius = this._radius;
		this._shrink_rate = this._start_radius / (shrink_time || 180); // Shrink to 0 over time
		this._active = 1;
		
		// Register as global safe zone for arena mode
		if (!entity_safe_zone_t._zones) {
			entity_safe_zone_t._zones = [];
		}
		entity_safe_zone_t._zones.push(this);
	}
	
	_update() {
		if (!this._active) return;
		
		// Shrink radius over time (minimum 256 units)
		let min_radius = 256;
		if (this._radius > min_radius) {
			this._radius = Math.max(min_radius, this._radius - this._shrink_rate * game_tick);
		}
		
		// Visual indicator - create light at boundary
		// This is subtle but helps players see the zone
		if (Math.floor(game_time * 2) % 2 === 0) {
			// Every half second, pulse light at random boundary position
			let angle = Math.random() * Math.PI * 2;
			let light_pos = vec3(
				this._center.x + Math.cos(angle) * this._radius,
				this.p.y + 128,
				this._center.z + Math.sin(angle) * this._radius
			);
			let light = game_spawn(entity_light_t, light_pos, 2, 0xff0000);
			light._die_at = game_time + 0.1;
		}
	}
	
	// Check if position is inside safe zone
	contains(pos) {
		let dist = vec3_dist(vec3(pos.x, 0, pos.z), this._center);
		return dist <= this._radius;
	}
	
	// Get distance from position to safe zone center
	distance_to_center(pos) {
		return vec3_dist(vec3(pos.x, 0, pos.z), this._center);
	}
	
	// Get distance from position to safe zone edge (negative if inside)
	distance_to_edge(pos) {
		return this.distance_to_center(pos) - this._radius;
	}
}

// Static list of all safe zones
entity_safe_zone_t._zones = [];
