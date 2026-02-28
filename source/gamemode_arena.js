// Arena Showdown Game Mode for Q1K3
// Single round, last-player-standing gameplay with shrinking safe zone

let
	arena_round_time = 180,
	arena_time_remaining = 180,
	arena_round_active = 0,
	arena_kills = 0,
	arena_winner = null,
	arena_spawn_points = [],
	arena_safe_zone = null,
	arena_bots = [],
	arena_bot_count = 3,
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
	
	// Find all spawn points
	arena_spawn_points = [];
	for (let e of game_entities) {
		if (e instanceof entity_spawn_point_t) {
			arena_spawn_points.push(e);
		}
	}
	
	// If no spawn points defined, use default positions at floor level
	if (arena_spawn_points.length === 0) {
		// Valid floor positions from m1.map (Y is vertical in Quake coords)
		arena_spawn_points = [
			{p: vec3(1088, 96, 712)},   // Original spawn - courtyard
			{p: vec3(100, 96, 1500)},  // West side
			{p: vec3(2000, 96, 1500)}, // East side  
			{p: vec3(1200, 96, 200)}   // North side
		];
	}
	
	// Spawn safe zone in center of arena
	arena_safe_zone = game_spawn(entity_safe_zone_t, vec3(1000, 0, 1500), 2500, 0);
	
	// Random spawn for player
	let spawn = arena_spawn_points[Math.floor(Math.random() * arena_spawn_points.length)];
	if (typeof game_entity_player !== 'undefined' && game_entity_player) {
		let player = game_entity_player;
		player.p = vec3_clone(spawn.p);
		player.p.y += 32; // Drop from sky
		player.v = vec3(0, 0, 0);
	}
	
	// Spawn 3 bot competitors
	arena_spawn_bots();
	
	console.log('Arena Showdown started! 3 minutes, last one standing wins!');
};

// Spawn AI competitors
arena_spawn_bots = () => {
	arena_bots = [];
	let used_spawns = [];
	
	for (let i = 0; i < arena_bot_count; i++) {
		// Find unused spawn point
		let available = arena_spawn_points.filter(s => !used_spawns.includes(s));
		if (available.length === 0) break;
		
		let spawn = available[Math.floor(Math.random() * available.length)];
		used_spawns.push(spawn);
		
		// Spawn bot
		let bot = game_spawn(entity_bot_player_t, vec3_clone(spawn.p));
		bot.p.y += 32; // Drop from sky
		arena_bots.push(bot);
	}
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
	
	// Count alive competitors (player + bots)
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
	
	// Check bots
	for (let bot of arena_bots) {
		if (!bot._dead) {
			alive_count++;
			last_alive = bot;
		}
	}
	
	// Win condition: only one remaining
	if (alive_count === 1 && last_alive) {
		arena_winner = last_alive;
		let winner_name = last_alive instanceof entity_bot_player_t ? 'BOT' : 'YOU';
		arena_end_round(winner_name + ' WINS!');
	}
	
	// Lose condition: player died but bots remain
	if (typeof game_entity_player !== 'undefined' && game_entity_player) {
		let player = game_entity_player;
		if (player._dead && alive_count > 0) {
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
		if (arena_winner instanceof entity_bot_player_t) {
			console.log('Winner: BOT');
		} else {
			console.log('Winner: YOU!');
		}
	}
};

// Draw arena UI - called from game.js render loop
arena_draw_ui = () => {
	// Format time as M:SS
	let mins = Math.floor(arena_time_remaining / 60);
	let secs = Math.floor(arena_time_remaining % 60);
	let time_str = mins + ':' + (secs < 10 ? '0' : '') + secs;
	
	// Draw timer and kill count at top of screen
	// This is a placeholder - actual UI would use canvas/webgl text
	/*DEBUG[*/
	if (arena_round_active) {
		console.log('Time:', time_str, '| Kills:', arena_kills);
	}
	/*]*/
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
			if (entity instanceof entity_bot_player_t) {
				arena_kills++;
			}
		}
		return true;
	}
	return false;
};
