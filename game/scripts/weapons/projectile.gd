class_name Projectile
extends Node2D
## 플레이어 투사체.

var velocity := Vector2.ZERO
var damage := 0.0
var pierce := 0
var life := 1.0
var knockback := 0.0
var color := Color.WHITE

var _already_hit: Array[Enemy] = []


func setup(at: Vector2, initial_velocity: Vector2, hit_damage: float, pierce_count: int, lifetime: float, knockback_speed: float, tint: Color) -> void:
	position = at
	velocity = initial_velocity
	damage = hit_damage
	pierce = pierce_count
	life = lifetime
	knockback = knockback_speed
	color = tint


func _ready() -> void:
	add_to_group(&"transient")


func _physics_process(delta: float) -> void:
	position += velocity * delta
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	for enemy: Enemy in get_tree().get_nodes_in_group(&"enemies"):
		if not enemy.is_alive() or _already_hit.has(enemy):
			continue
		if global_position.distance_to(enemy.global_position) <= enemy.radius + 3.0:
			enemy.take_hit(damage, global_position - velocity.normalized() * 10.0, knockback)
			_already_hit.append(enemy)
			pierce -= 1
			if pierce < 0:
				queue_free()
				return


func _draw() -> void:
	draw_line(Vector2.ZERO, -velocity.normalized() * 7.0, color, 2.0)
