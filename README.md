# notionScheduler

개인 Notion 스케줄러(Scheduler) 데이터베이스를 안전하고 일관되게 관리하기 위한 독립형 Python 인터페이스, CLI 도구 및 AI 에이전트 스킬입니다. 공식 `notion-client` SDK를 통한 직접 Notion API 연결을 기본 전송 방식으로 사용합니다.

CoursePilot의 LMS(학사 일정/과제) 수집 의존성 없이, 일상·업무 등 일반 태스크를 순수하게 관리할 수 있도록 분리된 독립 패키지입니다.

---

## 목차
- [주요 특징](#주요-특징)
- [스케줄러 데이터베이스 스키마](#스케줄러-데이터베이스-스키마)
- [설치 방법](#설치-방법)
  - [1. Python 패키지 / CLI 설치](#1-python-패키지--cli-설치)
  - [2. AI 에이전트 스킬(Skill) 등록](#2-ai-에이전트-스킬skill-등록)
- [환경 설정](#환경-설정)
- [사용 방법 (CLI)](#사용-방법-cli)
  - [기본 원칙: 프리뷰 및 적용 (Preview & Apply)](#기본-원칙-프리뷰-및-적용-preview--apply)
  - [1. 태스크 목록 조회 (`list`)](#1-태스크-목록-조회-list)
  - [2. 태스크 생성 (`create`)](#2-태스크-생성-create)
  - [3. 태스크 수정 (`update`)](#3-태스크-수정-update)
  - [4. 태스크 완료 (`complete`)](#4-태스크-완료-complete)
  - [5. 명시적 프리뷰 (`preview`)](#5-명시적-프리뷰-preview)
- [JSON 출력 규격 (Contract)](#json-출력-규격-contract)
- [테스트 실행](#테스트-실행)

---

## 주요 특징

- **CoursePilot과의 완전한 분리**: 학사 일정 수집 로직에 의존하지 않고, 개인 Notion 스케줄러 태스크 관리에만 집중합니다.
- **안전 제일 설계 (Dry-run by Default)**: 쓰기 명령(`create`, `update`, `complete`)은 `--apply` 플래그를 명시하지 않으면 실제 Notion에 반영되지 않고 변경 예정 사항(JSON 프리뷰)만 출력합니다.
- **AI 에이전트 친화적**: 모든 CLI 출력은 버전이 지정된 구조화된 JSON(`schema_version: 2`)으로 반환되어 Codex, Antigravity, Claude Code 등 AI 에이전트가 쉽게 파싱하고 검증할 수 있습니다.
- **보안 보장**: API 토큰 등 민감한 인증 정보는 콘솔 출력이나 오류 메시지에 일절 노출되지 않습니다.

---

## 스케줄러 데이터베이스 스키마

현재 개인 스케줄러(v0.2 기준)의 8개 프로퍼티 규격을 지원합니다:

| 프로퍼티 명 | Notion 타입 | 설명 및 허용 옵션 |
|---|---|---|
| **이름** | `title` | 태스크 제목 (필수) |
| **구분** | `multi_select` | 대분류 카테고리 (예: `일상`, `개발` 등) |
| **tag** | `multi_select` | 태그 (다중 선택 가능, 학업 동기화 시에도 값 보존) |
| **DueDate** | `date` | 마감일 (ISO 포맷: `YYYY-MM-DD` 또는 ISO 일시) |
| **Plan** | `date` | 계획/실행 예정일 (ISO 포맷) |
| **우선순위** | `select` | `🔴 긴급 (P1)`, `🟡 중요 (P2)`, `🔵 보통 (P3)`, `⚪ 낮음 (P4)` |
| **상태** | `status` | `시작 전`, `진행 중`, `완료`, `폐기` |
| **메모** | `rich_text` | 추가 메모 및 세부 설명 |

> **참고**: 이전 버전(v0.1)에 존재했던 `선택` 속성은 스키마에서 제외되었습니다.

---

## 설치 방법

### 1. Python 패키지 / CLI 설치

Python 3.11 이상 환경이 필요합니다.

#### 일반 pip 설치
```bash
pip install .
```

#### uv tool로 전역 CLI 설치
```bash
uv tool install .
```

#### 개발 환경 구성 (가상환경 및 테스트 의존성 포함)
```powershell
# 가상환경 생성 및 활성화
uv venv
.venv\Scripts\activate

# 편집 가능 모드 및 테스트 패키지 설치
uv pip install -e ".[test]"
```

설치가 완료되면 터미널에서 `notionScheduler` 명령어를 바로 사용할 수 있습니다.

---

### 2. AI 에이전트 스킬(Skill) 등록

이 패키지는 AI 에이전트가 스케줄러를 직접 조작할 수 있도록 안내하는 에이전트 스킬 파일(`SKILL.md`, `JSON_CONTRACT.md`)을 포함하고 있습니다.

#### Codex 에이전트에 스킬 등록 (PowerShell 예시)
```powershell
$skillSource = python -c "from pathlib import Path; import notion_scheduler; print(Path(notion_scheduler.__file__).parent / 'skill')"
$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skillDestination = Join-Path $codexRoot 'skills/notionScheduler'

New-Item -ItemType Directory -Force -Path $skillDestination | Out-Null
Copy-Item -LiteralPath (Join-Path $skillSource 'SKILL.md'), (Join-Path $skillSource 'JSON_CONTRACT.md') -Destination $skillDestination
```

#### Antigravity / Claude Code / 기타 에이전트
에이전트의 스킬 디렉터리(예: `~/.gemini/antigravity-cli/skills/notionScheduler` 또는 프로젝트 내 `.skills/notionScheduler`)에 [`skills/notionScheduler/`](skills/notionScheduler) 안의 파일들을 복사하여 배치하면 됩니다.

---

## 환경 설정

Notion API 호출을 위해 환경 변수를 설정해야 합니다.

### 필수 환경 변수

1. **인증 토큰 (택일)**:
   - `NOTION_TOKEN`: Notion 내부 통합(Integration) 시크릿 키 (권장)
   - `NOTION_API_KEY`: 토큰의 대체 키 이름

2. **대상 스케줄러 식별자 (아래 3가지 중 정확히 1개 설정)**:
   - `NOTION_DATA_SOURCE_ID`: 대상 Notion Data Source ID
   - `NOTION_DATABASE_ID`: 대상 Notion 데이터베이스 ID (32자리 UUID)
   - `NOTION_DATABASE_NAME`: 대상 Notion 데이터베이스 제목 (워크스페이스 내 고유해야 함)

> **주의**: Notion 통합 설정에서 해당 스케줄러 데이터베이스 페이지에 접근 권한(연결)이 부여되어 있어야 합니다.

### `.env` 파일 위치 및 사용 방법

`.env` 파일은 고정된 단일 경로가 강제되지 않으며, 사용자 및 에이전트의 운영 방식에 맞춰 아래 위치 중 편한 곳에 배치할 수 있습니다:

1. **프로젝트 루트 디렉터리 (권장)**:
   - 위치: `notionScheduler` 레포지토리 루트의 `.env`
   - 제공된 템플릿([`.env.example`](.env.example))을 복사하여 생성:
     ```powershell
     Copy-Item .env.example .env
     ```
   - 실행:
     ```bash
     notionScheduler --env-file .env list
     ```

2. **사용자 홈 디렉터리 (전역 공용 설정, 권장)**:
   - 위치: `~/.notionScheduler/.env` (또는 `$HOME/.notionScheduler.env`, `~/.config/notionScheduler/.env`)
   - 전역 표준 위치로 설정해 두면 CoursePilot을 포함한 모든 도구 및 프로젝트에서 자동으로 공용 참조합니다.
   - `notionScheduler`는 별도의 `--env-file` 옵션이 없어도 이 경로를 자동으로 감지하여 로드합니다:
     ```bash
     notionScheduler list
     ```

3. **기존 CoursePilot 설정 파일 재사용**:
   - CoursePilot에서 이미 동일한 Notion 토큰 및 Scheduler DB ID를 설정해 두었다면, 해당 `.env` 파일을 그대로 지정할 수 있습니다:
     ```bash
     notionScheduler --env-file ~/.coursepilot/.env list
     ```

> 💡 **Tip: `--env-file` 옵션 없이 바로 실행하고 싶다면?**  
> OS 시스템 환경 변수(Windows 시스템 설정)에 등록하거나, PowerShell 프로필(`$PROFILE`)에 등록해두면 파일 지정 없이 `notionScheduler list`처럼 바로 실행할 수 있습니다:
> ```powershell
> [Environment]::SetEnvironmentVariable("NOTION_TOKEN", "ntn_xxxx...", "User")
> [Environment]::SetEnvironmentVariable("NOTION_DATABASE_ID", "xxxx-xxxx...", "User")
> ```

> ⚠️ **주의**: `--env-file` 플래그를 사용할 경우 반드시 서브커맨드(`list`, `create` 등) **앞**에 위치해야 합니다.
> - 올바른 예: `notionScheduler --env-file .env list`
> - 잘못된 예: `notionScheduler list --env-file .env`

---

## 사용 방법 (CLI)

### 기본 원칙: 프리뷰 및 적용 (Preview & Apply)

- `create`, `update`, `complete` 명령은 기본적으로 **프리뷰 모드**(`dry_run: true`)로 동작합니다.
- 변경 사항을 실제로 데이터베이스에 적용하려면 반드시 **`--apply`** 플래그를 붙여야 합니다.

---

### 1. 태스크 목록 조회 (`list`)

스케줄러의 모든 태스크를 조회하거나 조건에 따라 필터링합니다.

```bash
# 전체 태스크 조회
notionScheduler list

# 상태별 필터링
notionScheduler list --status "시작 전"

# 제목 검색 (대소문자 구분 없음)
notionScheduler list --contains "보고서"

# 반환 개수 제한 및 필요한 필드만 축약 조회 (에이전트 컨텍스트 절약에 유용)
notionScheduler list --status "시작 전" --fields page_id,title,due_date,status --limit 10
```

#### 주요 옵션
- `--status <상태>`: 정확히 일치하는 상태만 조회 (`시작 전`, `진행 중`, `완료`, `폐기`)
- `--contains <문구>`: 제목에 특정 문구가 포함된 태스크만 필터링
- `--limit <숫자>`: 반환할 태스크의 최대 개수 (양의 정수)
- `--fields <필드목록>`: 반환할 필드를 쉼표로 구분하여 지정 (`page_id`는 항상 포함됨)

---

### 2. 태스크 생성 (`create`)

새로운 태스크를 생성합니다.

```bash
# 1) 생성 미리보기 (실제 반영되지 않음)
notionScheduler create --title "프로젝트 기획서 작성" --category "개발" --due-date "2026-10-15"

# 2) 실제 생성 적용 (--apply)
notionScheduler create --title "프로젝트 기획서 작성" --category "개발" --due-date "2026-10-15" --apply

# 태그 및 우선순위 지정 생성
notionScheduler create \
  --title "치과 정기 검진" \
  --category "일상" \
  --tag "건강" \
  --due-date "2026-10-20" \
  --priority "🟡 중요 (P2)" \
  --apply
```

#### 주요 옵션
- `--title <제목>`: 태스크 제목 (**필수**)
- `--category <구분>`: 카테고리 (반복 지정하여 다중 선택 가능)
- `--tag <태그>`: 태그 (반복 지정하여 다중 선택 가능)
- `--due-date <날짜>`: 마감일 (`YYYY-MM-DD` 또는 ISO 일시)
- `--plan-date <날짜>`: 실행 계획일
- `--priority <우선순위>`: 우선순위 선택 (`🔴 긴급 (P1)` 등)
- `--status <상태>`: 초기 상태 (기본값: 스케줄러 기본값 또는 `시작 전`)
- `--memo <내용>`: 메모 내용
- `--apply`: 실제 Notion에 생성 실행

---

### 3. 태스크 수정 (`update`)

기존 태스크의 속성을 부분 수정(sparse update)합니다. 지정하지 않은 속성은 그대로 유지됩니다.

```bash
# page_id 기준으로 수정 미리보기
notionScheduler update --page-id "1aa53280-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --plan-date "2026-10-14" --status "진행 중"

# 실제 수정 적용 (--apply)
notionScheduler update --page-id "1aa53280-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --plan-date "2026-10-14" --status "진행 중" --apply

# 제목으로 단일 페이지를 검색하여 수정 (결과가 정확히 1건일 때만 동작)
notionScheduler update --lookup-title "치과 정기 검진" --due-date "2026-10-22" --apply

# 태그 수정 (기존 태그에 추가/대체)
notionScheduler update --page-id "<PAGE_ID>" --tag "예약완료" --apply

# 모든 태그 제거
notionScheduler update --page-id "<PAGE_ID>" --clear-tags --apply
```

#### 대상 지정 옵션 (둘 중 하나 필수)
- `--page-id <ID>`: 수정할 대상 Notion 페이지 ID (가장 안전하고 권장됨)
- `--lookup-title <제목>`: 대상 페이지 제목 검색 (동일 제목이 2개 이상이면 에러 반환)

---

### 4. 태스크 완료 (`complete`)

태스크의 상태를 `완료`로 변경하는 전용 단축 명령어입니다.

```bash
# 완료 처리 미리보기
notionScheduler complete --page-id "<PAGE_ID>"

# 실제 완료 처리 적용 (--apply)
notionScheduler complete --page-id "<PAGE_ID>" --apply
```

---

### 5. 명시적 프리뷰 (`preview`)

`create`, `update`, `complete` 동작을 명시적으로 프리뷰 전용으로 호출합니다.

```bash
notionScheduler preview create --title "새로운 일정"
notionScheduler preview update --page-id "<PAGE_ID>" --status "완료"
notionScheduler preview complete --page-id "<PAGE_ID>"
```

---

## JSON 출력 규격 (Contract)

모든 명령어는 `stdout` 표준 출력을 통해 단일 JSON 객체를 반환합니다:

- **공통 필드**:
  - `schema_version`: `2` (고정)
  - `ok`: `true` (성공 시) 또는 `false` (오류 시)

### 성공 응답 예시 (조회 `list`)
```json
{
  "schema_version": 2,
  "ok": true,
  "action": "list",
  "tasks": [
    {
      "page_id": "1aa53280-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "title": "프로젝트 기획서 작성",
      "category": ["개발"],
      "tags": ["중요"],
      "due_date": "2026-10-15",
      "plan_date": null,
      "priority": "🔴 긴급 (P1)",
      "status": "시작 전",
      "memo": ""
    }
  ],
  "count": 1,
  "matching_count": 1
}
```

### 성공 응답 예시 (생성 프리뷰 `create` / `dry_run: true`)
```json
{
  "schema_version": 2,
  "ok": true,
  "action": "create",
  "dry_run": true,
  "target": {
    "database_id": "...",
    "data_source_id": "...",
    "title": "Scheduler"
  },
  "page_id": null,
  "before": null,
  "properties": {
    "이름": { "title": [{ "text": { "content": "프로젝트 기획서 작성" } }] },
    "DueDate": { "date": { "start": "2026-10-15" } }
  },
  "result": null
}
```

### 성공 응답 예시 (실제 생성 적용 `--apply` / `dry_run: false`)
```json
{
  "schema_version": 2,
  "ok": true,
  "action": "create",
  "dry_run": false,
  "target": { ... },
  "page_id": null,
  "before": null,
  "properties": { ... },
  "result": {
    "id": "2bb64391-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
  }
}
```

### 오류 응답 예시
오류 발생 시 프로세스는 종료 코드 `2`를 반환하며 아래 JSON을 출력합니다:
```json
{
  "schema_version": 2,
  "ok": false,
  "error": {
    "code": "InputError",
    "message": "--title is required for create."
  }
}
```

---

## 테스트 실행

로컬 단위 테스트 및 스킬 규격 테스트를 실행할 수 있습니다:

```bash
pytest
```
