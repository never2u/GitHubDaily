extends Node
## 전역 이벤트 버스. 시스템 간 결합을 줄이기 위해 시그널로만 통신한다.

signal enemy_killed(enemy_data: Resource, at: Vector2)
## source: &"weapon" | &"ultimate" — 얼티밋 피해는 게이지 충전에서 제외한다.
signal damage_dealt(amount: float, source: StringName)
signal player_hp_changed(hp: float, max_hp: float)
signal player_died
signal coins_changed(total: int)
signal ultimate_charge_changed(ratio: float)
signal ultimate_activated(ultimate: Resource)
