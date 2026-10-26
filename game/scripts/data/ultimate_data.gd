class_name UltimateData
extends Resource
## 클래스 고유 얼티밋 정의.

## AROUND_PLAYER: 플레이어 주변 범위에 주기적 피해 (검풍난무)
## RANDOM_STRIKES: 범위 내 적 위치에 무작위 타격 (화살비)
enum Pattern { AROUND_PLAYER, RANDOM_STRIKES }

@export var id: StringName
@export var display_name: String
@export var pattern: Pattern = Pattern.AROUND_PLAYER
@export var damage: float = 15.0
@export var radius: float = 90.0
@export var duration: float = 2.0
@export var tick_interval: float = 0.2
@export var knockback: float = 120.0
@export var strike_radius: float = 32.0
@export var strikes_per_tick: int = 3
@export var color: Color = Color.WHITE
