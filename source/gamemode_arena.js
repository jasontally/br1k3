// Arena Showdown Game Mode for Q1K3
// Single round, last-player-standing gameplay with shrinking safe zone
// Uses existing enemy AI (grunts, enforcers, hounds) as competitors

let
	arena_round_time = 180,
	arena_time_remaining = 180,
	arena_round_active = 0,
	arena_kills = 0,
	arena_winner = null,
	arena_safe_zone = null,
	game_state = 0,
	GAME_STATE_ARENA = 1,
	GAME_STATE_POST_ROUND = 2;

// Initialize arena mode - called when game starts
arena_init = () => {
	// Reset state
	arena_round_active = 1;
	arena_time_remaining = 180;
	arena_kills = 0;
	arena_winner = null;
	game_state = GAME_STATE_ARENA;
	
	// Spawn safe zone in center of arena
	arena_safe_zone = game_spawn(entity_safe_zone_t, vec3(1000, 0, 1500), 2500, 0);
	
	// Player keeps original map spawn position
	// Just reset velocity to ensure clean start
	if (typeof game_entity_player !== 'undefined' && game_entity_player) {
		game_entity_player.v = vec3(0, 0, 0);
	}
	
	console.log('Arena Showdown started! 3 minutes, last one standing wins!');
	console.log('Existing enemies in map:', count_enemies(), 'competitors');
};

// Count existing enemy entities
let count_enemies = () => {
	let count = 0;
	for (let e of game_entities) {
		if (e instanceof entity_enemy_grunt_t || 
		    e instanceof entity_enemy_enforcer_t || 
		    e instanceof entity_enemy_hound_t ||
		    e instanceof entity_enemy_ogre_t ||
		    e instanceof entity_enemy_zombie_t) {
			count++;
		}
	}
	return count;
};

// Update arena mode - called every frame from game.js
arena_update = () => {
	if (!arena_round_active || game_state !== GAME_STATE_ARENA) return;
	
	// Countdown timer
	arena_time_remaining -= game_tick;
	if (arena_time_remaining <= 0) {
		arena_end_round('TIME UP');
		return;
	}
	
	// Count alive competitors (player + existing enemies)
	let alive_count = 0;
	let last_alive = null;
	
	// Check player
	if (typeof game_entity_player !== 'undefined' && game_entity_player) {
		let player = game_entity_player;
		if (!player._dead) {
			alive_count++;
			last_alive = player;
		}
	}
	
	// Check existing enemies
	let enemies_alive = 0;
	for (let e of game_entities) {
		if ((e instanceof entity_enemy_grunt_t || 
		     e instanceof entity_enemy_enforcer_t || 
		     e instanceof entity_enemy_hound_t ||
		     e instanceof entity_enemy_ogre_t ||
		     e instanceof entity_enemy_zombie_t) && !e._dead) {
			enemies_alive++;
			alive_count++;
			last_alive = e;
		}
	}
	
	// Win condition: only one remaining
	if (alive_count === 1 && last_alive) {
		arena_winner = last_alive;
		let winner_name = last_alive instanceof entity_player_t ? 'YOU' : 'ENEMY';
		arena_end_round(winner_name + ' WIN!');
	}
	
	// Lose condition: player died but enemies remain
	if (typeof game_entity_player !== 'undefined' && game_entity_player) {
		let player = game_entity_player;
		if (player._dead && enemies_alive > 0) {
			arena_end_round('ELIMINATED');
		}
	}
};

// End round and show results
arena_end_round = (reason) => {
	arena_round_active = 0;
	game_state = GAME_STATE_POST_ROUND;
	
	console.log('=== ARENA ROUND END ===');
	console.log('Result:', reason);
	console.log('Kills:', arena_kills);
	console.log('Time:', Math.floor(180 - arena_time_remaining), 'seconds');
	
	if (arena_winner) {
		if (arena_winner instanceof entity_player_t) {
			console.log('Winner: YOU!');
		} else {
			console.log('Winner: ENEMY');
		}
	}
};

// Safe zone damage check - called from player/enemy update
arena_check_safe_zone = (entity) => {
	if (!arena_safe_zone || !arena_round_active) return false;
	
	let dist = vec3_dist(vec3(entity.p.x, 0, entity.p.z), arena_safe_zone._center);
	if (dist > arena_safe_zone._radius) {
		// Outside safe zone - take damage
		entity._health -= 10 * game_tick;
		entity._pain = 1; // Show pain effect
		
		if (entity._health <= 0 && !entity._dead) {
			entity._kill();
			// Track kills
			if (entity instanceof entity_enemy_grunt_t || 
			    entity instanceof entity_enemy_enforcer_t || 
			    entity instanceof entity_enemy_hound_t) {
				arena_kills++;
			}
		}
		return true;
	}
	return false;
};
