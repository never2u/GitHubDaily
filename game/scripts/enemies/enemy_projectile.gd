class_name EnemyProjectile
extends Node2D
## 적 투사체.

const HIT_RADIUS := 3.0
const LIFETIME := 4.0

var velocity := Vector2.ZERO
var damage := 0.0
var arena: Arena

var _life := LIFETIME


func setup(at: Vector2, initial_velocity: Vector2, hit_damage: float, owner_arena: Arena) -> void:
	position = at
	velocity = initial_velocity
	damage = hit_damage
	arena = owner_arena


func _ready() -> void:
	add_to_group(&"transient")


func _physics_process(delta: float) -> void:
	position += velocity * delta
	_life -= delta
	if _life <= 0.0 or not Arena.BOUNDS.has_point(position):
		queue_free()
		return
	var player := arena.player
	if player.is_alive() and global_position.distance_to(player.global_position) <= Player.RADIUS + HIT_RADIUS:
		player.take_damage(damage)
		queue_free()


func _draw() -> void:
	draw_circle(Vector2.ZERO, HIT_RADIUS, Color(1.0, 0.45, 0.2))
