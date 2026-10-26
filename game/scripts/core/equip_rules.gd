class_name EquipRules
extends RefCounted
## 클래스-무기 장착 규칙. 상점 진열, 구매, 장착 모두 이 함수를 사용한다.

const HAND_SLOTS := 2
const MAX_WEAPON_SLOTS := 6
const MAX_AUX_SLOTS := MAX_WEAPON_SLOTS - HAND_SLOTS


static func can_equip(class_data: ClassData, weapon: WeaponData) -> bool:
	if weapon.slot_type == WeaponData.SlotType.TWO_HAND:
		return class_data.two_hand_only
	if class_data.two_hand_only and weapon.slot_type == WeaponData.SlotType.HAND:
		return false
	if weapon.attack_type == WeaponData.AttackType.MELEE and not class_data.can_use_melee:
		return false
	if weapon.attack_type == WeaponData.AttackType.RANGED and not class_data.can_use_ranged:
		return false
	return true


## 무기가 차지하는 손 슬롯 수 (보조 무기는 0)
static func hand_slot_cost(weapon: WeaponData) -> int:
	match weapon.slot_type:
		WeaponData.SlotType.TWO_HAND:
			return 2
		WeaponData.SlotType.HAND:
			return 1
	return 0
