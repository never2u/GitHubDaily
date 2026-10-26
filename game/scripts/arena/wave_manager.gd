class_name WaveManager
extends Node
## 웨이브 타이머와 적 생성. 시간이 다 되면 wave_finished 를 보낸다.

signal wave_finished

const ENEMY_SLAVE := preload("res://data/enemies/slave_gladiator.tres")
const ENEMY_WOLF := preload("res://data/enemies/wolf.tres")
const ENEMY_ARCHER := preload("res://data/enemies/archer.tres")
const ENEMY_LION := preload("res://data/enemies/lion.tres")

const MAX_ALIVE_ENEMIES := 150
const MIN_SPAWN_DISTANCE := 140.0

var arena: Arena
var wave := 0
var duration := 0.0
var time_left := 0.0

var _spawn_left := 0.0
var _running := false


static func wave_duration(wave_number: int) -> float:
	return minf(20.0 + (wave_number - 1) * 5.0, 60.0)


func start_wave(wave_number: int) -> void:
	wave = wave_number
	duration = wave_duration(wave)
	time_left = duration
	_spawn_left = 0.5
	_running = true


func stop() -> void:
	_running = false


func _physics_process(delta: float) -> void:
	if not _running:
		return
	time_left -= delta
	if time_left <= 0.0:
		time_left = 0.0
		_running = false
		wave_finished.emit()
		return
	_spawn_left -= delta
	if _spawn_left <= 0.0:
		_spawn_left = _spawn_interval()
		_spawn_group()


func _spawn_interval() -> float:
	return maxf(0.35, 1.6 - wave * 0.15)


func _spawn_group() -> void:
	var count := 1 + int(wave / 2.0)
	var hp_mult := 1.0 + (wave - 1) * 0.3
	var damage_mult := 1.0 + (wave - 1) * 0.15
	for i in count:
		if arena.enemies().size() >= MAX_ALIVE_ENEMIES:
			return
		var marker := SpawnMarker.new()
		marker.setup(_pick_enemy(), arena, hp_mult, damage_mult)
		marker.position = arena.random_spawn_point(MIN_SPAWN_DISTANCE)
		arena.add_entity(marker)


## 웨이브가 진행될수록 등장하는 적 종류가 늘어난다.
func _pick_enemy() -> EnemyData:
	var pool: Array = [[ENEMY_SLAVE, 10.0]]
	if wave >= 2:
		pool.append([ENEMY_WOLF, 3.0 + wave])
	if wave >= 3:
		pool.append([ENEMY_ARCHER, 1.0 + wave * 0.5])
	if wave >= 4:
		pool.append([ENEMY_LION, wave * 0.6])
	var total := 0.0
	for entry in pool:
		total += entry[1]
	var roll := randf() * total
	for entry in pool:
		roll -= entry[1]
		if roll <= 0.0:
			return entry[0]
	return ENEMY_SLAVE
