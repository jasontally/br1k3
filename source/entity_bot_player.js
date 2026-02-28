// Bot Player - AI competitor for arena mode
// Inherits from entity_player_t but adds AI decision making

class entity_bot_player_t extends entity_player_t {
	_init() {
		// Initialize as player with default weapon (shotgun)
		this._model = model_grunt;
		this._texture = 4;
		this._health = 100;
		this._max_health = 100;
		this._weapon = new weapon_shotgun_t;
		this._weapons = [this._weapon];
		this._ammo = [0, 50, 10]; // Shells, nails, grenades
		this._speed = 240;
		this._dead = 0;
		this._pain = 0;
		
		// Bot-specific AI state
		this._ai_state = 'hunt'; // hunt, loot, flee, wander
		this._ai_target = null;
		this._ai_target_pos = null;
		this._ai_reaction_time = 0;
		this._ai_next_action = 0;
		this._ai_path_timer = 0;
		this._is_bot = 1;
		this._bot_name = 'BOT-' + Math.floor(Math.random() * 999);
		
		// Track this bot globally
		if (!entity_bot_player_t._bots) {
			entity_bot_player_t._bots = [];
		}
		entity_bot_player_t._bots.push(this);
		
		// Add to enemy group so player can shoot them
		game_entities_enemies.push(this);
	}
	
	_update() {
		if (this._dead) return;
		
		// Update AI decision making
		this._ai_think();
		
		// Execute AI actions
		this._ai_execute();
		
		// Check safe zone damage
		if (entity_safe_zone_t._zones && entity_safe_zone_t._zones.length > 0) {
			let zone = entity_safe_zone_t._zones[0];
			if (!zone.contains(this.p)) {
				// Outside safe zone - prioritize moving toward center
				this._ai_target_pos = zone._center;
				this._ai_state = 'flee';
				
				// Take damage
				this._health -= 10 * game_tick;
				this._pain = 1;
				if (this._health <= 0) {
					this._kill();
					return;
				}
			}
		}
		
		// Use parent player physics and rendering
		this._update_physics();
		this._draw_model();
	}
	
	// AI decision making
	_ai_think() {
		if (game_time < this._ai_next_action) return;
		
		// Update reaction timer
		this._ai_reaction_time -= game_tick;
		if (this._ai_reaction_time > 0) return;
		
		// Scan for targets (player and other bots)
		let best_target = null;
		let best_dist = 99999;
		
		// Check player
		if (entity_player_t._instances && entity_player_t._instances.length > 0) {
			let player = entity_player_t._instances[0];
			if (!player._dead) {
				let dist = vec3_dist(this.p, player.p);
				if (dist < best_dist && this._can_see(player.p)) {
					best_dist = dist;
					best_target = player;
				}
			}
		}
		
		// Check other bots
		for (let bot of entity_bot_player_t._bots) {
			if (bot !== this && !bot._dead) {
				let dist = vec3_dist(this.p, bot.p);
				if (dist < best_dist && this._can_see(bot.p)) {
					best_dist = dist;
					best_target = bot;
				}
			}
		}
		
		// Decide state based on situation
		if (this._health < 30) {
			// Low health - flee and look for health
			this._ai_state = 'flee';
			this._find_nearest_pickup('health');
		} else if (best_target && best_dist < 600) {
			// Target in range - attack
			this._ai_state = 'hunt';
			this._ai_target = best_target;
			this._ai_target_pos = vec3_clone(best_target.p);
		} else if (this._weapon instanceof weapon_shotgun_t && this._ammo[0] < 10) {
			// Low ammo - look for better weapon
			this._ai_state = 'loot';
			this._find_nearest_pickup('weapon');
		} else {
			// Wander
			this._ai_state = 'wander';
			if (game_time > this._ai_path_timer) {
				this._ai_pick_random_destination();
				this._ai_path_timer = game_time + 3;
			}
		}
		
		// Set next action time (reaction delay 0.1-0.3s)
		this._ai_next_action = game_time + 0.1 + Math.random() * 0.2;
	}
	
	// Execute AI actions based on current state
	_ai_execute() {
		switch (this._ai_state) {
			case 'hunt':
				this._ai_hunt();
				break;
			case 'flee':
				this._ai_flee();
				break;
			case 'loot':
				this._ai_loot();
				break;
			case 'wander':
			default:
				this._ai_wander();
				break;
		}
	}
	
	// Hunt state - move toward target and shoot
	_ai_hunt() {
		if (!this._ai_target || this._ai_target._dead) {
			this._ai_state = 'wander';
			return;
		}
		
		let target_pos = this._ai_target.p;
		let dist = vec3_dist(this.p, target_pos);
		
		// Update target position periodically
		if (game_time > this._ai_path_timer) {
			this._ai_target_pos = vec3_clone(target_pos);
			this._ai_path_timer = game_time + 0.5;
		}
		
		// Move toward target but keep some distance
		let desired_dist = 300;
		if (dist > desired_dist + 100) {
			// Move closer
			this._ai_move_toward(this._ai_target_pos);
		} else if (dist < desired_dist - 100) {
			// Move away
			let away_dir = vec3_normalize(vec3_sub(this.p, this._ai_target_pos));
			let away_pos = vec3_add(this.p, vec3_mulf(away_dir, 200));
			this._ai_move_toward(away_pos);
		}
		
		// Aim at target and shoot
		this._ai_aim_at(target_pos);
		if (dist < 800 && this._can_see(target_pos)) {
			this._ai_shoot();
		}
	}
	
	// Flee state - run away and look for health
	_ai_flee() {
		if (this._ai_target_pos) {
			this._ai_move_toward(this._ai_target_pos);
		} else {
			this._ai_wander();
		}
	}
	
	// Loot state - move toward pickup
	_ai_loot() {
		if (this._ai_target_pos) {
			let dist = vec3_dist(this.p, this._ai_target_pos);
			if (dist > 64) {
				this._ai_move_toward(this._ai_target_pos);
			} else {
				// Reached pickup, go back to hunting
				this._ai_state = 'wander';
			}
		} else {
			this._ai_wander();
		}
	}
	
	// Wander state - move to random destination
	_ai_wander() {
		if (this._ai_target_pos) {
			let dist = vec3_dist(this.p, this._ai_target_pos);
			if (dist > 64) {
				this._ai_move_toward(this._ai_target_pos);
			} else {
				// Reached destination, pick new one
				this._ai_pick_random_destination();
			}
		} else {
			this._ai_pick_random_destination();
		}
	}
	
	// Movement helpers
	_ai_move_toward(target_pos) {
		// Calculate direction
		let dir = vec3_sub(target_pos, this.p);
		dir.y = 0; // Keep on ground plane
		dir = vec3_normalize(dir);
		
		// Set velocity toward target
		this.v.x = dir.x * this._speed;
		this.v.z = dir.z * this._speed;
		
		// Set yaw to face movement direction
		this.yaw = Math.atan2(dir.x, dir.z);
	}
	
	_ai_aim_at(target_pos) {
		// Calculate angles to look at target
		let dir = vec3_sub(target_pos, this.p);
		let dist = vec3_length(dir);
		
		// Yaw (horizontal)
		this.yaw = Math.atan2(dir.x, dir.z);
		
		// Pitch (vertical) - aim slightly up for distance
		this.pitch = Math.atan2(dir.y, Math.sqrt(dir.x * dir.x + dir.z * dir.z));
	}
	
	_ai_shoot() {
		// Fire current weapon
		if (this._weapon && this._weapon._shoot) {
			this._weapon._shoot(this);
		}
	}
	
	// Check if we can see a position (line of sight)
	_can_see(pos) {
		// Simple check - no wall collision detection yet
		// Just check distance and angle
		let dir = vec3_sub(pos, this.p);
		let dist = vec3_length(dir);
		
		if (dist > 1200) return false;
		
		// Check if within view angle (90 degrees)
		let angle_to_target = Math.atan2(dir.x, dir.z);
		let angle_diff = angle_to_target - this.yaw;
		while (angle_diff > Math.PI) angle_diff -= Math.PI * 2;
		while (angle_diff < -Math.PI) angle_diff += Math.PI * 2;
		
		return Math.abs(angle_diff) < Math.PI / 2;
	}
	
	// Find nearest pickup of a type
	_find_nearest_pickup(type) {
		let best_dist = 99999;
		let best_pickup = null;
		
		for (let e of game_entities) {
			let is_match = false;
			if (type === 'health' && e instanceof entity_pickup_health_t) is_match = true;
			if (type === 'weapon' && (e instanceof entity_pickup_nailgun_t || e instanceof entity_pickup_grenadelauncher_t)) is_match = true;
			
			if (is_match) {
				let dist = vec3_dist(this.p, e.p);
				if (dist < best_dist) {
					best_dist = dist;
					best_pickup = e;
				}
			}
		}
		
		if (best_pickup) {
			this._ai_target_pos = vec3_clone(best_pickup.p);
		}
	}
	
	// Pick random destination in arena
	_ai_pick_random_destination() {
		// Random position within arena bounds (roughly)
		let x = 200 + Math.random() * 1800;
		let z = 200 + Math.random() * 2800;
		let y = 500; // Will fall to ground
		this._ai_target_pos = vec3(x, y, z);
	}
	
	_kill() {
		// Drop weapon on death
		if (this._weapon && !(this._weapon instanceof weapon_shotgun_t)) {
			// Could spawn weapon pickup here
		}
		
		// Call parent kill
		super._kill();
		
		// Remove from bot list
		entity_bot_player_t._bots = entity_bot_player_t._bots.filter(b => b !== this);
	}
}

// Track all bots
entity_bot_player_t._bots = [];
