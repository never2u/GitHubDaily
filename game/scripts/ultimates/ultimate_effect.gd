class_name UltimateEffect
extends Node2D
## 얼티밋 발동 효과. 지속 시간 동안 일정 간격으로 피해를 준다.

const STRIKE_VISUAL_TIME := 0.25

var data: UltimateData
var player: Player
var arena: Arena

var _elapsed := 0.0
var _tick_left := 0.0
## [{pos: Vector2, time: float}] — 화살비 타격 지점 표시용 (전역 좌표)
var _strikes: Array[Dictionary] = []


func setup(ultimate: UltimateData, owner_player: Player, owner_arena: Arena) -> void:
	data = ultimate
	player = owner_player
	arena = owner_arena
	position = player.global_position


func _ready() -> void:
	add_to_group(&"transient")


func _physics_process(delta: float) -> void:
	global_position = player.global_position
	_elapsed += delta
	_tick_left -= delta
	if _tick_left <= 0.0:
		_tick_left = data.tick_interval
		_pulse()
	var remaining: Array[Dictionary] = []
	for strike in _strikes:
		strike.time -= delta
		if strike.time > 0.0:
			remaining.append(strike)
	_strikes = remaining
	queue_redraw()
	if _elapsed >= data.duration and _strikes.is_empty():
		queue_free()


func _pulse() -> void:
	if _elapsed > data.duration:
		return
	match data.pattern:
		UltimateData.Pattern.AROUND_PLAYER:
			_damage_circle(global_position, data.radius)
		UltimateData.Pattern.RANDOM_STRIKES:
			for i in data.strikes_per_tick:
				var center := _pick_strike_point()
				_damage_circle(center, data.strike_radius)
				_strikes.append({pos = center, time = STRIKE_VISUAL_TIME})


func _pick_strike_point() -> Vector2:
	var candidates: Array[Enemy] = []
	for enemy: Enemy in arena.enemies():
		if enemy.is_alive() and enemy.global_position.distance_to(global_position) <= data.radius:
			candidates.append(enemy)
	if not candidates.is_empty():
		return candidates.pick_random().global_position
	return global_position + Vector2.from_angle(randf() * TAU) * randf() * data.radius


func _damage_circle(center: Vector2, circle_radius: float) -> void:
	for enemy: Enemy in arena.enemies():
		if enemy.global_position.distance_to(center) <= circle_radius + enemy.radius:
			enemy.take_hit(data.damage, center, data.knockback, &"ultimate")


func _draw() -> void:
	var color := data.color
	if _elapsed <= data.duration:
		match data.pattern:
			UltimateData.Pattern.AROUND_PLAYER:
				var spin := _elapsed * 12.0
				for i in 3:
					var start := spin + i * TAU / 3.0
					draw_arc(Vector2.ZERO, data.radius, start, start + 1.2, 12, color, 3.0)
				color.a = 0.15
				draw_circle(Vector2.ZERO, data.radius, color)
			UltimateData.Pattern.RANDOM_STRIKES:
				color.a = 0.25
				draw_arc(Vector2.ZERO, data.radius, 0.0, TAU, 48, color, 1.0)
	for strike in _strikes:
		var strike_color := data.color
		strike_color.a = strike.time / STRIKE_VISUAL_TIME
		var local: Vector2 = strike.pos - global_position
		draw_circle(local, data.strike_radius, Color(strike_color, strike_color.a * 0.3))
		draw_line(local + Vector2(0, -data.strike_radius * 1.5), local, strike_color, 2.0)
