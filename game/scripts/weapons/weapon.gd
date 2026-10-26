class_name Weapon
extends Node2D
## 장착 무기. 사거리 안의 가장 가까운 적을 자동으로 공격한다.

const SWING_TIME := 0.15

var data: WeaponData
var player: Player

var _cooldown_left := 0.0
var _swing_left := 0.0
var _aim := Vector2.RIGHT


func setup(weapon_data: WeaponData, owner_player: Player) -> void:
	data = weapon_data
	player = owner_player
	_cooldown_left = randf() * data.cooldown * 0.5


func is_melee() -> bool:
	return data.attack_type == WeaponData.AttackType.MELEE


func effective_damage() -> float:
	var c := player.class_data
	return data.damage * (c.melee_damage_mult if is_melee() else c.ranged_damage_mult)


func effective_range() -> float:
	return data.attack_range * (1.0 if is_melee() else player.class_data.ranged_range_mult)


func effective_cooldown() -> float:
	return data.cooldown / (player.class_data.melee_attack_speed_mult if is_melee() else 1.0)


func _physics_process(delta: float) -> void:
	_cooldown_left -= delta
	_swing_left = maxf(0.0, _swing_left - delta)
	queue_redraw()
	if not player.is_alive():
		return
	var target := player.arena.nearest_enemy(global_position, effective_range())
	if target == null:
		return
	_aim = global_position.direction_to(target.global_position)
	if _cooldown_left <= 0.0:
		_attack()
		_cooldown_left = effective_cooldown()


func _attack() -> void:
	if is_melee():
		_swing()
	else:
		_shoot()


func _swing() -> void:
	_swing_left = SWING_TIME
	var half_arc := deg_to_rad(data.swing_arc_deg) * 0.5
	var reach := effective_range()
	for enemy: Enemy in player.arena.enemies():
		var to_enemy := enemy.global_position - global_position
		if to_enemy.length() > reach + enemy.radius:
			continue
		if absf(_aim.angle_to(to_enemy)) <= half_arc:
			enemy.take_hit(effective_damage(), global_position, data.knockback)


func _shoot() -> void:
	var projectile := Projectile.new()
	var life := effective_range() / data.projectile_speed
	projectile.setup(global_position, _aim * data.projectile_speed, effective_damage(), data.pierce, life, data.knockback, data.color)
	player.arena.add_entity(projectile)


func _draw() -> void:
	if data == null:
		return
	draw_line(Vector2.ZERO, _aim * 9.0, data.color, 2.0)
	if is_melee() and _swing_left > 0.0:
		var half_arc := deg_to_rad(data.swing_arc_deg) * 0.5
		var faded := data.color
		faded.a = _swing_left / SWING_TIME
		draw_arc(Vector2.ZERO, effective_range(), _aim.angle() - half_arc, _aim.angle() + half_arc, 16, faded, 2.0)
