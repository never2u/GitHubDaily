class_name Enemy
extends Node2D
## 적. 행동 패턴은 EnemyData.behavior 로 결정된다.

enum State { MOVE, WINDUP, DASH, RECOVER }

const KNOCKBACK_DECAY := 900.0
const SEPARATION_STRENGTH := 0.8

var data: EnemyData
var arena: Arena
var max_hp: float
var hp: float
var radius: float
var contact_damage: float
var shot_damage: float

var _dead := false
var _flash := 0.0
var _knock := Vector2.ZERO
var _state := State.MOVE
var _state_time := 0.0
var _dash_dir := Vector2.ZERO
var _shot_cooldown := 0.0


func setup(enemy_data: EnemyData, owner_arena: Arena, hp_mult: float, damage_mult: float) -> void:
	data = enemy_data
	arena = owner_arena
	max_hp = data.max_hp * hp_mult
	hp = max_hp
	radius = data.radius
	contact_damage = data.contact_damage * damage_mult
	shot_damage = data.shot_damage * damage_mult
	_shot_cooldown = data.shot_cooldown * randf_range(0.5, 1.0)


func _ready() -> void:
	add_to_group(&"enemies")


func is_alive() -> bool:
	return not _dead


func _physics_process(delta: float) -> void:
	if _dead:
		return
	var player := arena.player
	var to_player := player.global_position - global_position
	var dist := to_player.length()
	var dir := to_player / dist if dist > 0.001 else Vector2.ZERO

	var move := Vector2.ZERO
	match data.behavior:
		EnemyData.Behavior.CHASER:
			move = dir * data.speed
		EnemyData.Behavior.CHARGER:
			move = _update_charger(dir, dist, delta)
		EnemyData.Behavior.SHOOTER:
			move = _update_shooter(dir, dist, delta)
	if _state != State.DASH:
		move += _separation() * data.speed * SEPARATION_STRENGTH

	position = arena.clamp_to_bounds(position + (move + _knock) * delta, radius)
	_knock = _knock.move_toward(Vector2.ZERO, KNOCKBACK_DECAY * delta)
	_flash = maxf(0.0, _flash - delta)

	if player.is_alive() and global_position.distance_to(player.global_position) < radius + Player.RADIUS:
		player.take_damage(contact_damage)
	queue_redraw()


func take_hit(amount: float, from: Vector2, knockback: float, source: StringName = &"weapon") -> void:
	if _dead:
		return
	var dealt := minf(amount, hp)
	hp -= amount
	_flash = 0.08
	if knockback > 0.0 and _state != State.DASH:
		_knock = from.direction_to(global_position) * knockback
	EventBus.damage_dealt.emit(dealt, source)
	if hp <= 0.0:
		_die()


func _die() -> void:
	_dead = true
	EventBus.enemy_killed.emit(data, global_position)
	arena.spawn_coins(global_position, data.coin_drop)
	queue_free()


func _update_charger(dir: Vector2, dist: float, delta: float) -> Vector2:
	_state_time -= delta
	match _state:
		State.MOVE:
			if dist < data.charge_trigger_range:
				_state = State.WINDUP
				_state_time = data.charge_windup
				_dash_dir = dir
				return Vector2.ZERO
			return dir * data.speed
		State.WINDUP:
			if _state_time <= 0.0:
				_state = State.DASH
				_state_time = data.charge_duration
			return Vector2.ZERO
		State.DASH:
			if _state_time <= 0.0:
				_state = State.RECOVER
				_state_time = 0.8
			return _dash_dir * data.charge_speed
		State.RECOVER:
			if _state_time <= 0.0:
				_state = State.MOVE
			return dir * data.speed * 0.4
	return Vector2.ZERO


func _update_shooter(dir: Vector2, dist: float, delta: float) -> Vector2:
	_shot_cooldown -= delta
	if _shot_cooldown <= 0.0 and dist < data.preferred_distance * 2.0:
		_shot_cooldown = data.shot_cooldown
		var shot := EnemyProjectile.new()
		shot.setup(global_position, dir * data.shot_speed, shot_damage, arena)
		arena.add_entity(shot)
	if dist > data.preferred_distance + 20.0:
		return dir * data.speed
	if dist < data.preferred_distance - 20.0:
		return -dir * data.speed
	return dir.orthogonal() * data.speed * 0.5


func _separation() -> Vector2:
	var push := Vector2.ZERO
	for other: Enemy in arena.enemies():
		if other == self:
			continue
		var offset := global_position - other.global_position
		var dist := offset.length()
		var min_dist := radius + other.radius
		if dist < min_dist and dist > 0.01:
			push += offset / dist * (min_dist - dist) / min_dist
	return push


func _draw() -> void:
	var body := Color.WHITE if _flash > 0.0 else data.color
	draw_circle(Vector2.ZERO, radius, body)
	draw_arc(Vector2.ZERO, radius, 0.0, TAU, 20, Color.BLACK, 1.0)
	if _state == State.WINDUP:
		draw_line(Vector2(0, -radius - 10), Vector2(0, -radius - 4), Color.YELLOW, 2.0)
		draw_line(Vector2(0, -radius - 2), Vector2(0, -radius - 1), Color.YELLOW, 2.0)
	if hp < max_hp:
		var width := radius * 2.0
		var top_left := Vector2(-radius, -radius - 5)
		draw_rect(Rect2(top_left, Vector2(width, 2)), Color(0, 0, 0, 0.6))
		draw_rect(Rect2(top_left, Vector2(width * maxf(hp, 0.0) / max_hp, 2)), Color.RED)
