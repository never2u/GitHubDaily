class_name Player
extends Node2D
## 플레이어. 이동만 직접 조작하고, 무기는 자동 공격한다.

const RADIUS := 9.0
const INVULN_TIME := 0.5
const HAND_OFFSETS: Array[Vector2] = [Vector2(-9, 2), Vector2(9, 2)]
## 적에게 준 피해 100당 게이지 1%
const CHARGE_PER_DAMAGE_DEALT := 0.01
## 최대 체력의 1%를 잃을 때마다 게이지 1%
const CHARGE_PER_HP_PERCENT_LOST := 1.0
const ARMOR_SCALE := 15.0

var class_data: ClassData
var arena: Arena
var max_hp: float
var hp: float
var move_speed: float
var armor: float
## 얼티밋 게이지 0~100
var ult_charge := 0.0
var weapons: Array[Weapon] = []
var facing := Vector2.RIGHT

var _invuln := 0.0
var _dead := false


func setup(selected_class: ClassData, owner_arena: Arena) -> void:
	class_data = selected_class
	arena = owner_arena
	max_hp = class_data.max_hp
	hp = max_hp
	move_speed = class_data.move_speed
	armor = class_data.armor
	_equip_starting_weapons()


func _ready() -> void:
	EventBus.enemy_killed.connect(_on_enemy_killed)
	EventBus.damage_dealt.connect(_on_damage_dealt)
	_emit_status()


func _physics_process(delta: float) -> void:
	if _dead:
		return
	var dir := Input.get_vector(&"move_left", &"move_right", &"move_up", &"move_down")
	if dir != Vector2.ZERO:
		facing = dir.normalized()
	position = arena.clamp_to_bounds(position + dir * move_speed * delta, RADIUS)
	_invuln = maxf(0.0, _invuln - delta)
	if Input.is_action_just_pressed(&"ultimate"):
		try_ultimate()
	queue_redraw()


func is_alive() -> bool:
	return not _dead


## 웨이브 시작 시 체력을 회복하고 중앙으로 복귀한다. 얼티밋 게이지는 유지된다.
func reset_for_wave() -> void:
	hp = max_hp
	_invuln = 0.0
	position = Vector2.ZERO
	_emit_status()


func take_damage(amount: float) -> void:
	if _dead or _invuln > 0.0:
		return
	var taken := amount * _armor_multiplier()
	hp = maxf(0.0, hp - taken)
	_invuln = INVULN_TIME
	add_charge(taken / max_hp * 100.0 * CHARGE_PER_HP_PERCENT_LOST * class_data.charge_taken_mult)
	EventBus.player_hp_changed.emit(hp, max_hp)
	if hp <= 0.0:
		_dead = true
		queue_redraw()
		EventBus.player_died.emit()


func add_charge(amount: float) -> void:
	if amount <= 0.0 or _dead:
		return
	ult_charge = minf(100.0, ult_charge + amount)
	EventBus.ultimate_charge_changed.emit(ult_charge / 100.0)


func try_ultimate() -> void:
	if ult_charge < 100.0 or class_data.ultimate == null:
		return
	ult_charge = 0.0
	EventBus.ultimate_charge_changed.emit(0.0)
	arena.spawn_ultimate(class_data.ultimate, self)
	EventBus.ultimate_activated.emit(class_data.ultimate)


func _equip_starting_weapons() -> void:
	var hand_slots_used := 0
	for weapon_data: WeaponData in class_data.starting_weapons:
		if not EquipRules.can_equip(class_data, weapon_data):
			push_warning("%s 클래스는 %s 을(를) 장착할 수 없습니다." % [class_data.display_name, weapon_data.display_name])
			continue
		var cost := EquipRules.hand_slot_cost(weapon_data)
		if hand_slots_used + cost > EquipRules.HAND_SLOTS:
			continue
		var weapon := Weapon.new()
		weapon.position = HAND_OFFSETS[mini(hand_slots_used, HAND_OFFSETS.size() - 1)]
		weapon.setup(weapon_data, self)
		add_child(weapon)
		weapons.append(weapon)
		hand_slots_used += cost


## 방어가 양수면 피해 감소, 음수면 피해 증가
func _armor_multiplier() -> float:
	if armor >= 0.0:
		return ARMOR_SCALE / (ARMOR_SCALE + armor)
	return (ARMOR_SCALE - armor) / ARMOR_SCALE


func _emit_status() -> void:
	EventBus.player_hp_changed.emit(hp, max_hp)
	EventBus.ultimate_charge_changed.emit(ult_charge / 100.0)


func _on_enemy_killed(enemy_data: Resource, _at: Vector2) -> void:
	add_charge((enemy_data as EnemyData).ult_charge * class_data.charge_kill_mult)


func _on_damage_dealt(amount: float, source: StringName) -> void:
	if source == &"ultimate":
		return
	add_charge(amount * CHARGE_PER_DAMAGE_DEALT * class_data.charge_dealt_mult)


func _draw() -> void:
	var body := class_data.color if class_data else Color.WHITE
	if _dead:
		body = body.darkened(0.6)
	elif _invuln > 0.0 and int(_invuln * 20.0) % 2 == 0:
		body.a = 0.35
	draw_circle(Vector2.ZERO, RADIUS, body)
	draw_arc(Vector2.ZERO, RADIUS, 0.0, TAU, 24, Color.BLACK, 1.0)
	draw_circle(facing * (RADIUS - 3.0), 2.0, Color.BLACK)
