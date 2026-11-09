# 오늘의 환전 (@hwanjeon.board)

평일 아침 하나은행 첫 고시환율로 공항 전광판 스타일 카드 7장(1장은 영상)을 만들어 인스타그램에 올리는 봇.

## 흐름
1. `daily.yml`: 평일 09:15 KST 실행 → `bot.main build`가 환율 수집, `data/history.json`에 기록, `docs/posts/날짜/`에 카드 생성
2. 커밋·푸시 → GitHub Pages(`main` 브랜치 `/docs`)로 공개
3. `bot.main publish`가 Pages 주소로 인스타 캐러셀 게시

## 설정
| 종류 | 이름 | 설명 |
|---|---|---|
| Secret | `IG_ACCESS_TOKEN` | 메타 개발자 앱에서 받은 토큰 |
| Secret | `IG_USER_ID` | 인스타 계정 ID |
| Variable | `POST_ENABLED` | `true`일 때만 실제 게시. 없으면 카드만 만드는 확인 모드 |
| Variable | `HANA_PBLD_DV_CD` | 하나은행 고시구분 값 (최초 고시). 기본 `1` (probe로 확인함), `도구 → probe`로 확인 |
| Variable | `IG_GRAPH_HOST` | 기본 `graph.facebook.com`. `도구 → whoami`로 되는 쪽 확인 |

## 안전장치
- 주말·공휴일(오늘 고시 없음)은 게시 안 함
- 전일 대비 3% 넘게 움직인 통화가 있으면 게시 중단하고 워크플로 실패 → 메일 알림
- 같은 날짜는 두 번 게시 안 함 (`posted.json`)

## 로컬 테스트
```
pip install -r requirements.txt && python -m playwright install chromium
python -m tests.sample /tmp/sample   # 가짜 데이터로 카드 생성
python -m pytest -q
```
