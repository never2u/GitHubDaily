# 깃허브 데일리 (GitHub Daily)

GitHub에서 지금 가장 뜨거운 저장소들을 모아 **신문처럼** 보여주는 서비스입니다.
매일 아침 GitHub Actions가 데이터를 모으고, 정적 사이트(GitHub Pages)와 RSS 피드를 발행합니다.

## 지면 구성

| 코너 | 내용 | 데이터 |
| --- | --- | --- |
| 오늘의 브리핑 | 오늘 가장 뜨거운 저장소, 신규 진입, 주요 언어, 장기 흥행작 요약 | 트렌딩 + 지난 호 비교 |
| 오늘의 톱뉴스 | 하루 동안 별을 가장 많이 받은 저장소를 헤드라인으로 | `github.com/trending?since=daily` |
| 함께 떠오르는 저장소 | 2~6위 | 〃 |
| 오늘의 언어 지형 | 트렌딩 저장소의 언어 분포 | 〃 |
| 오늘의 트렌딩 | 전체 목록 + 언어 필터, `NEW` / `▲순위상승` / `N일 연속` 배지 | 〃 |
| 갓 태어난 신작 | 최근 7일 안에 생성된 저장소 중 별이 많은 순 | GitHub Search API |
| 이번 주 화제 · 이번 달 결산 | 주간/월간 트렌딩 | `since=weekly`, `since=monthly` |

헤드라인은 지난 호와 비교해 자동으로 작성됩니다 (예: “신규 진입 foo, 하루 만에 ★1.2k 돌풍”,
“bar, 순위 7계단 급상승”, “5일 연속 트렌딩, 식지 않는 baz 열풍”).

발행물:
- `index.html` — 오늘 호
- `archive/YYYY-MM-DD.html`, `archive.html` — 지난 호
- `feed.xml` — RSS (최근 20호)

## 한국어 번역

저장소 설명은 Claude Haiku 5.5(`claude-haiku-5-5`)로 한국어로 번역합니다. 원문 영어는 마우스를 올리면 툴팁으로 보입니다.

- **번역 캐시** `data/translations.json`: 이미 번역한 저장소는 다시 번역하지 않고, 설명이 바뀐 경우에만 새로 번역합니다.
- 새로 번역할 설명을 40개씩 묶어 요청하므로 보통 하루 1~2번 호출, 한 달 비용은 1달러 미만입니다.
- `ANTHROPIC_API_KEY`가 없거나 API 호출이 실패하면 영어 원문을 그대로 보여 줍니다(사이트 빌드는 계속됩니다).

설정: [Claude Console](https://console.anthropic.com)에서 API 키를 발급받아 저장소
**Settings → Secrets and variables → Actions**에 `ANTHROPIC_API_KEY`로 등록하세요.
Console의 사용 한도(spend limit)를 낮게 걸어 두면 예상 밖 과금을 막을 수 있습니다.

## 실행

수집·렌더링은 Python 3.10+ 표준 라이브러리만 사용합니다. 번역을 쓰려면 `pip install -r requirements.txt`가 필요합니다.

```bash
python -m ghnews               # 오늘 데이터 수집 → data/YYYY-MM-DD.json 저장 → site/ 생성
python -m ghnews --no-fetch    # 저장된 데이터로 사이트만 다시 생성
python -m ghnews --no-translate  # 번역 없이 수집·생성
python -m unittest discover -s tests -t .
```

`GITHUB_TOKEN` 환경 변수가 있으면 Search API 호출에 사용합니다 (요청 한도 상향).

## 배포 (GitHub Pages)

1. 저장소 **Settings → Pages → Source** 를 **GitHub Actions** 로 설정합니다.
2. `.github/workflows/daily.yml` 이 매일 오전 8시(KST) 전에 실행되어 새 호를 발행하고,
   수집한 데이터(`data/`)를 커밋해 다음 날 비교(신규 진입·순위 변동·연속 일수)에 사용합니다.
3. Actions 탭에서 **Daily edition → Run workflow** 로 즉시 발행할 수도 있습니다.

## 구조

```
ghnews/
  fetch.py      # 트렌딩 페이지 스크래핑 + Search API 수집
  editorial.py  # 배지·헤드라인·브리핑 생성 (순수 함수)
  render.py     # HTML / RSS 렌더링
  translate.py  # Claude Haiku 5.5 한국어 번역 + 캐시
  __main__.py   # CLI
data/           # 호별 수집 데이터 (JSON), translations.json 번역 캐시
tests/          # 파서·편집 로직·빌드 테스트
```

트렌딩 페이지 수집이 실패하면 Search API 결과로 대체하고, 그 사실을 지면에 표시합니다.
