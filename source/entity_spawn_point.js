// Spawn point entity for arena mode multiplayer
// Just a marker - doesn't render or collide

class entity_spawn_point_t extends entity_t {
	_init() {
		this._check_against = ENTITY_GROUP_NONE;
		this._angle = 0;
		
		// Register in global spawn point list
		if (!entity_spawn_point_t._spawn_points) {
			entity_spawn_point_t._spawn_points = [];
		}
		entity_spawn_point_t._spawn_points.push(this);
	}
	
	_update() {
		// Spawn points do nothing - just exist as markers
		// Could add visual effect here if desired
	}
}

// Static list of all spawn points
entity_spawn_point_t._spawn_points = [];
