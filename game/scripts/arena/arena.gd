class_name Arena
extends Node2D
## 전투 씬 루트. 웨이브 진행, 엔티티 생성, 웨이브 사이 화면 전환을 관리한다.

signal run_finished(victory: bool, wave: int)

enum Phase { FIGHT, INTERMISSION, OVER }

const BOUNDS := Rect2(-480, -300, 960, 600)
const WALL_THICKNESS := 40.0
## M0 는 1막(6웨이브) 분량만 진행한다.
const LAST_WAVE := 6

var class_data: ClassData
var player: Player
var phase := Phase.FIGHT

var _entities: Node2D
var _waves: WaveManager
var _hud: Hud
var _overlay_layer: CanvasLayer
var _overlay: Control


func _ready() -> void:
	# 일시정지 중에도 입력(재개)을 받기 위해 루트는 항상 동작하고,
	# 게임플레이 노드만 일시정지 대상이 된다.
	process_mode = Node.PROCESS_MODE_ALWAYS
	RunState.start_run(class_data)

	_waves = WaveManager.new()
	_waves.arena = self
	_waves.process_mode = Node.PROCESS_MODE_PAUSABLE
	_waves.wave_finished.connect(_on_wave_finished)
	add_child(_waves)

	_hud = Hud.new()
	_hud.waves = _waves
	add_child(_hud)

	_overlay_layer = CanvasLayer.new()
	_overlay_layer.layer = 10
	add_child(_overlay_layer)

	_entities = Node2D.new()
	_entities.y_sort_enabled = true
	_entities.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(_entities)

	player = Player.new()
	player.setup(class_data, self)
	_entities.add_child(player)

	var camera := Camera2D.new()
	camera.position_smoothing_enabled = true
	camera.limit_left = int(BOUNDS.position.x - WALL_THICKNESS)
	camera.limit_top = int(BOUNDS.position.y - WALL_THICKNESS)
	camera.limit_right = int(BOUNDS.end.x + WALL_THICKNESS)
	camera.limit_bottom = int(BOUNDS.end.y + WALL_THICKNESS)
	player.add_child(camera)

	EventBus.player_died.connect(_on_player_died)
	_start_next_wave()


func _exit_tree() -> void:
	get_tree().paused = false


func _unhandled_input(event: InputEvent) -> void:
	if phase == Phase.FIGHT and event.is_action_pressed(&"pause"):
		_set_paused(not get_tree().paused)
		get_viewport().set_input_as_handled()


# --- 엔티티 API --------------------------------------------------------------

func clamp_to_bounds(point: Vector2, margin: float) -> Vector2:
	return Vector2(
		clampf(point.x, BOUNDS.position.x + margin, BOUNDS.end.x - margin),
		clampf(point.y, BOUNDS.position.y + margin, BOUNDS.end.y - margin))


func enemies() -> Array[Node]:
	return get_tree().get_nodes_in_group(&"enemies")


func nearest_enemy(from: Vector2, max_range: float) -> Enemy:
	var best: Enemy = null
	var best_dist := max_range
	for enemy: Enemy in enemies():
		if not enemy.is_alive():
			continue
		var dist := from.distance_to(enemy.global_position) - enemy.radius
		if dist <= best_dist:
			best = enemy
			best_dist = dist
	return best


func add_entity(node: Node2D) -> void:
	_entities.add_child(node)


func spawn_enemy(data: EnemyData, at: Vector2, hp_mult: float, damage_mult: float) -> void:
	var enemy := Enemy.new()
	enemy.setup(data, self, hp_mult, damage_mult)
	enemy.position = at
	add_entity(enemy)


func spawn_coins(at: Vector2, count: int) -> void:
	for i in count:
		var coin := Coin.new()
		coin.arena = self
		coin.position = at + Vector2(randf_range(-6, 6), randf_range(-6, 6))
		add_entity(coin)


func spawn_ultimate(ultimate: UltimateData, owner_player: Player) -> void:
	var effect := UltimateEffect.new()
	effect.setup(ultimate, owner_player, self)
	add_entity(effect)


func random_spawn_point(min_distance_from_player: float) -> Vector2:
	var area := BOUNDS.grow(-24.0)
	var point := Vector2.ZERO
	for attempt in 12:
		point = Vector2(randf_range(area.position.x, area.end.x), randf_range(area.position.y, area.end.y))
		if point.distance_to(player.global_position) >= min_distance_from_player:
			break
	return point


# --- 웨이브 흐름 -------------------------------------------------------------

func _start_next_wave() -> void:
	_close_overlay()
	RunState.wave += 1
	phase = Phase.FIGHT
	player.reset_for_wave()
	_entities.process_mode = Node.PROCESS_MODE_PAUSABLE
	_waves.start_wave(RunState.wave)


func _on_wave_finished() -> void:
	if phase != Phase.FIGHT:
		return
	_clear_field()
	if RunState.wave >= LAST_WAVE:
		_finish(true)
		return
	phase = Phase.INTERMISSION
	_entities.process_mode = Node.PROCESS_MODE_DISABLED
	_show_overlay(UiKit.make_dialog(
		"웨이브 %d 클리어!" % RunState.wave,
		"보유 데나리우스: %d\n얼티밋 게이지: %d%%\n\n(상점은 M1 에서 추가됩니다)" % [RunState.coins, int(player.ult_charge)],
		[["다음 웨이브 ▶", _start_next_wave]]))


func _on_player_died() -> void:
	if phase == Phase.OVER:
		return
	_waves.stop()
	_finish(false)


func _finish(victory: bool) -> void:
	phase = Phase.OVER
	_entities.process_mode = Node.PROCESS_MODE_DISABLED
	var title := "1막 생존 성공!" if victory else "패배..."
	var body := "도달 웨이브: %d / %d\n획득 데나리우스: %d" % [RunState.wave, LAST_WAVE, RunState.coins]
	_show_overlay(UiKit.make_dialog(title, body,
		[["클래스 선택으로", func() -> void: run_finished.emit(victory, RunState.wave)]]))


## 웨이브 종료: 남은 적과 투사체를 제거하고, 바닥의 데나리우스를 자동 회수한다.
func _clear_field() -> void:
	for coin: Coin in get_tree().get_nodes_in_group(&"coins"):
		coin.collect()
	for node in enemies() + get_tree().get_nodes_in_group(&"transient"):
		node.queue_free()


func _set_paused(paused: bool) -> void:
	get_tree().paused = paused
	if paused:
		_show_overlay(UiKit.make_dialog("일시정지", "이동: WASD / 왼쪽 스틱\n얼티밋: Space / RB",
			[["계속하기", func() -> void: _set_paused(false)]]))
	else:
		_close_overlay()


func _show_overlay(control: Control) -> void:
	_close_overlay()
	_overlay = control
	_overlay_layer.add_child(_overlay)


func _close_overlay() -> void:
	if is_instance_valid(_overlay):
		_overlay.queue_free()
	_overlay = null


# --- 그리기 ------------------------------------------------------------------

func _draw() -> void:
	draw_rect(BOUNDS.grow(WALL_THICKNESS), Color(0.35, 0.22, 0.18))
	draw_rect(BOUNDS, Color(0.86, 0.74, 0.52))
	var line := Color(0.72, 0.6, 0.4)
	draw_arc(Vector2.ZERO, 80.0, 0.0, TAU, 48, line, 2.0)
	draw_arc(Vector2.ZERO, 200.0, 0.0, TAU, 64, line, 1.0)
	draw_line(Vector2(BOUNDS.position.x, 0), Vector2(BOUNDS.end.x, 0), line, 1.0)
	draw_rect(BOUNDS, Color(0.25, 0.15, 0.12), false, 3.0)
