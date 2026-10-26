class_name ClassData
extends Resource
## 클래스 정의: 장착 제한, 강점/페널티 배율, 고유 얼티밋.

@export var id: StringName
@export var display_name: String
@export_multiline var description: String
@export var color: Color = Color.WHITE

@export_group("Stats")
@export var max_hp: float = 30.0
@export var move_speed: float = 110.0
@export var armor: float = 0.0
@export var melee_damage_mult: float = 1.0
@export var melee_attack_speed_mult: float = 1.0
@export var ranged_damage_mult: float = 1.0
@export var ranged_range_mult: float = 1.0

@export_group("Equip Rules")
@export var can_use_melee: bool = true
@export var can_use_ranged: bool = true
## 버서커: 손 슬롯에 양손 무기 1개만 사용
@export var two_hand_only: bool = false
## 시작 시 열려 있는 보조 슬롯 수
@export var starting_aux_slots: int = 0
## WeaponData 목록
@export var starting_weapons: Array = []

@export_group("Ultimate")
@export var ultimate: UltimateData
@export var charge_kill_mult: float = 1.0
@export var charge_dealt_mult: float = 1.0
@export var charge_taken_mult: float = 1.0
