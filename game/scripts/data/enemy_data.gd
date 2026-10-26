class_name EnemyData
extends Resource
## 적 정의. 웨이브에 따른 체력/피해 배율은 WaveManager 가 곱한다.

enum Behavior { CHASER, CHARGER, SHOOTER }

@export var id: StringName
@export var display_name: String
@export var behavior: Behavior = Behavior.CHASER
@export var max_hp: float = 10.0
@export var speed: float = 60.0
@export var contact_damage: float = 4.0
@export var radius: float = 8.0
@export var color: Color = Color.INDIAN_RED
@export var coin_drop: int = 1
## 처치 시 얼티밋 게이지 충전량(%)
@export var ult_charge: float = 0.5

@export_group("Charger")
@export var charge_trigger_range: float = 130.0
@export var charge_windup: float = 0.6
@export var charge_duration: float = 0.45
@export var charge_speed: float = 260.0

@export_group("Shooter")
@export var preferred_distance: float = 150.0
@export var shot_cooldown: float = 2.2
@export var shot_speed: float = 150.0
@export var shot_damage: float = 4.0
