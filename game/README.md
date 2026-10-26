# Chrono Gladiator — Godot 프로젝트 (M0 프로토타입)

기획서: [`../docs/GDD.md`](../docs/GDD.md)

## 실행 방법
1. [Godot 4.4 이상](https://godotengine.org/download)을 설치합니다. 표준 버전이면 되고, .NET 버전은 필요 없습니다.
2. Godot 프로젝트 매니저에서 **가져오기**를 누르고 이 `game/` 폴더의 `project.godot`을 선택합니다.
3. **F5**를 눌러 실행합니다.

## 조작
| 행동 | 키보드 | 게임패드 |
|---|---|---|
| 이동 | WASD / 방향키 | 왼쪽 스틱 / D패드 |
| 얼티밋 | Space | RB / Y |
| 일시정지 | Esc | Start |
| 메뉴 선택 | 마우스 / Enter | A |

## M0 범위
- 클래스 2종 (검사, 궁수). 장착 제한과 강점·페널티 배율이 적용됩니다.
- 손 슬롯 2개 자동 공격 (근접 베기 / 원거리 투사체)
- 적 4종: 노예 검투사(추적), 늑대(빠른 추적), 궁수(거리 유지 사격), 사자(돌진)
- 웨이브 타이머 (20초 + 5초씩 증가), 6웨이브(1막 분량)
- 적이 등장하기 전 위치를 예고 표시합니다.
- 데나리우스 드롭과 자석 회수. 웨이브가 끝나면 바닥에 남은 것을 자동 회수합니다.
- 얼티밋 게이지는 처치, 준 피해, 받은 피해로 찹니다. 클래스 고유 얼티밋은 검풍난무와 화살비입니다.
- 웨이브 사이 화면 (상점 자리), 일시정지, 패배·승리 화면

모든 그래픽은 도형으로 대체한 상태입니다. 수치는 `data/` 폴더의 `.tres` 파일에서 조정합니다.

## 구조
```
scripts/
  autoload/   EventBus(시그널), GameInput(입력 등록), RunState(런 상태)
  data/       WeaponData, EnemyData, ClassData, UltimateData (Resource)
  core/       EquipRules — 클래스·무기 장착 규칙
  arena/      Arena(전투 루트), WaveManager, SpawnMarker
  player/ weapons/ enemies/ pickups/ ultimates/ ui/
data/         .tres 밸런스 데이터
```
