class_name WeaponData
extends Resource
## 무기 정의. 밸런스 수치는 data/weapons/*.tres 에서 조정한다.

enum AttackType { MELEE, RANGED }
## HAND: 한 손 슬롯 · TWO_HAND: 손 슬롯 2칸 (버서커 전용) · AUX: 보조 슬롯
enum SlotType { HAND, TWO_HAND, AUX }

@export var id: StringName
@export var display_name: String
@export var attack_type: AttackType = AttackType.MELEE
@export var slot_type: SlotType = SlotType.HAND
## 계열 태그 (blade, polearm, thrown, bow, beast, divine, chrono)
@export var tags: PackedStringArray = PackedStringArray()
@export var damage: float = 10.0
## 공격 간격(초)
@export var cooldown: float = 1.0
@export var attack_range: float = 60.0
## 근접 무기의 베기 각도
@export var swing_arc_deg: float = 90.0
## 넉백 초기 속도 (px/s)
@export var knockback: float = 120.0
@export var projectile_speed: float = 300.0
## 원거리 투사체가 관통하는 적 수
@export var pierce: int = 0
@export var color: Color = Color.WHITE
