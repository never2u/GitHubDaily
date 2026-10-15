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

## 실행

Python 3.10+ 표준 라이브러리만 사용합니다. 별도 설치가 필요 없습니다.

```bash
python -m ghnews               # 오늘 데이터 수집 → data/YYYY-MM-DD.json 저장 → site/ 생성
python -m ghnews --no-fetch    # 저장된 데이터로 사이트만 다시 생성
python -m unittest discover -s tests -t .
```

`GITHUB_TOKEN` 환경 변수가 있으면 Search API 호출에 사용합니다 (요청 한도 상향).

## 배포 (GitHub Pages)

1. 저장소 **Settings → Pages → Source** 를 **GitHub Actions** 로 설정합니다.
2. `.github/workflows/daily.yml` 이 매일 09:13 (KST)에 실행되어 새 호를 발행하고,
   수집한 데이터(`data/`)를 커밋해 다음 날 비교(신규 진입·순위 변동·연속 일수)에 사용합니다.
3. Actions 탭에서 **Daily edition → Run workflow** 로 즉시 발행할 수도 있습니다.

## 구조

```
ghnews/
  fetch.py      # 트렌딩 페이지 스크래핑 + Search API 수집
  editorial.py  # 배지·헤드라인·브리핑 생성 (순수 함수)
  render.py     # HTML / RSS 렌더링
  __main__.py   # CLI
data/           # 호별 수집 데이터 (JSON)
tests/          # 파서·편집 로직·빌드 테스트
```

트렌딩 페이지 수집이 실패하면 Search API 결과로 대체하고, 그 사실을 지면에 표시합니다.
