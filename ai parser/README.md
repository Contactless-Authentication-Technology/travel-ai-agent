## CREATE_PLAN Parser (FastAPI + LLM Structured Output)

이 프로젝트는 사용자 자연어 여행 요청을 **CREATE_PLAN 전용 JSON 스키마**로 변환하는 **Parser API**입니다.  
게이트웨이/라우터/MCP 이전 단계로, 지금은 **파서만** 구현되어 있습니다.

### 기술 스택

- **언어**: Python
- **웹 프레임워크**: FastAPI
- **스키마/검증**: Pydantic v2
- **LLM 연동**: OpenAI Responses API (`json_schema` 기반 Structured Output)

---

## 설치 및 실행

### 1. 의존성 설치

프로젝트 루트에서:

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

LLM 호출을 위해 다음 환경 변수가 필요합니다.

- **필수**
  - `OPENAI_API_KEY`: OpenAI API 키
- **선택**
  - `OPENAI_RESPONSE_MODEL`: Responses API 모델 이름 (기본값: `gpt-4.1-mini`)

예시 (zsh/bash):

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_RESPONSE_MODEL="gpt-4.1-mini"
```

### 3. 서버 실행

```bash
uvicorn main:app --reload
```

기본 주소: `http://127.0.0.1:8000`

FastAPI 자동 문서:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 엔드포인트 개요

### POST `/agent/run`

단일 Agent 엔드포인트입니다.  
요청 메시지를 파싱하고 Router가 실행 여부를 판단합니다.

- **Request Body**

```json
{
  "message": "파리 3박 4일 일정 만들어줘. 카페 많이, 걷기는 적게.",
  "context": {}
}
```

- **Response Body**

공통 응답 형태:

```json
{
  "status": "ASK | DONE | ERROR",
  "intent": "CREATE_PLAN",
  "trip_id": "",
  "data": {},
  "clarify": {
    "needed": false,
    "missing_fields": []
  }
}
```

- `status=ASK`: `missing_fields`가 있어 추가 입력이 필요한 상태
- `status=DONE`: Parser 통과 + 실행(MCP 스텁) 완료
- `status=ERROR`: 아직 미구현 intent 등 오류 상태

`data.plan` 안에는 `CreatePlanPayload` 구조가 저장됩니다.

최상위 구조:

- **intent**: 항상 `"CREATE_PLAN"`
- **destination**: `{ city: "Paris"(기본), country: "FR"(기본) }`
- **dates**: `{ start_date: null, end_date: null, days: int>=1|null, source: "explicit" | "missing" }`
- **party**: `{ adult: number, highschool: number, middleschool: number, elementary: number, toddler: number, trip_style: "solo" | "couple" | "friends" | "family" | "unknown" }`
- **lodging**: `{ text: string|null, lat: number|null, lng: number|null }`
- **mobility**:
  - `travel_mode`: `"walk" | "transit" | "both"` (기본 `"both"`)
  - `optimize`: `"min_time" | "min_transfers"` (기본 `"min_time"`)
  - `max_walk_km_per_day`: number|null
  - `wheelchair`: boolean
  - `stroller`: boolean
- **pace**:
  - `level`: `"slow" | "normal" | "fast"` (기본 `"normal"`)
  - `max_places_per_day`: 기본 6
- **budget**:
  - `currency`: `"EUR"`
  - `budget_total`: number|null
  - `budget_per_day`: number|null
  - `budget_mode`: `"save" | "normal" | "flex"` (기본 `"normal"`)
- **preferences**:
  - `weights`: `{ cafe, museum, park, shopping, night_view }` (0~1, 기본 0.5)
  - `themes`: string[]
  - `must_include`: string[]
  - `must_avoid`: string[]
- **constraints**:
  - `museum_per_day`: number|null
  - `indoor_focus`: boolean
  - `rainy_plan`: boolean
- **output**:
  - `include_map`: true
  - `include_excel`: true
  - `include_cost`: true
- **clarify**:
  - `needed`: boolean (기본 false)
  - `missing_fields`: string[]  (`Parser`가 질문 대신 누락 필드만 전달)

---

## LLM Structured Output 동작 방식

- LLM 호출은 `create_plan_parser.py`의 `_call_llm_structured` 에서 처리합니다.
- `CreatePlanPayload.model_json_schema()`를 사용해 **JSON Schema를 생성**하고,
  OpenAI Chat Completions API에 `response_format.type = "json_schema"` + `"strict": true`로 전달합니다.
- LLM 응답은:
  1. `json.loads`로 파싱
  2. `CreatePlanPayload.model_validate(...)` 로 Pydantic 검증
  3. 검증 실패 시 **최대 1회 재시도 (총 2회)**
  4. 2회 모두 실패 시 `LLMStructuredOutputError` 발생 → FastAPI에서 HTTP 500 반환

이 과정에서 프롬프트에 `"JSON으로 출력해줘"` 같은 지시문은 넣지 않고,  
**스키마 강제 + 검증**으로만 JSON 구조를 보장합니다.

---

## 규칙 기반 후처리 로직

LLM이 생성한 초안 JSON 위에, `create_plan_parser.py`의 `_apply_rule_overrides` 가 **규칙 기반으로 값을 덮어씁니다.**

- **intent / destination**
  - `intent`는 항상 `"CREATE_PLAN"`으로 강제
  - 파리 전용 MVP로 `destination.city = "Paris"`, `destination.country = "FR"` 고정

- **기간 / days 추출**
  - `"2025년7월23일~2025년7월26일"` → `days = 4`, `start_date/end_date` ISO 설정
  - `"7월23일~7월26일"` 또는 `"7월23일부터26일까지"` → 현재 연도 기준 ISO 설정 
  -  달이 넘어가는건 아직 mvp에 구현 안됨(추가 구현 예정)
  - `"3박 4일"`, `"3박4일"` → `days = 4`, `source = "explicit"`
  - `"2박 3일"`, `"2박3일"` → `days = 3`
  - `"5일"` → `days = 5`
  - 위 패턴이 없으면 → `days = null`, `source = "missing"` (missing_fields에 `dates.days` 기록)
  - 날짜 범위를 추출하지 못하면 `start_date`, `end_date`는 `null`

- **이동 수단 / 최적화**
  - `"도보 위주"` → `travel_mode = "walk"`
  - `"대중교통 위주"` → `travel_mode = "transit"`
  - 둘 다/없음 → 이상한 값이면 `"both"`로 보정
  - `"환승 최소"`, `"환승 적게"` → `optimize = "min_transfers"`
  - 그 외/이상한 값 → `optimize = "min_time"`

- **페이스**
  - `"여유롭게"` → `pace.level = "slow"`
  - `"빡세게"` → `pace.level = "fast"`
  - 그 외/이상한 값 → `pace.level = "normal"`
  - `max_places_per_day` 비어 있으면 항상 6

- **걷기 제한**
  - `"하루 7km 이하"`, `"7km 이하"` → 숫자 추출 후 `max_walk_km_per_day = 7`

- **보조 이동 제약**
  - `"휠체어"` 포함 → `wheelchair = true`
  - `"유모차"` 포함 → `stroller = true`

- **날씨/실내**
  - `"비 오면"`, `"비오면"`, `"비 올 때"`, `"우천"` → `rainy_plan = true`
  - `"실내 위주"` → `indoor_focus = true`

- **취향 가중치**
  - 기본적으로 `cafe/museum/park/shopping/night_view = 0.5`
  - `"카페 많이"`, `"카페 위주"`:
    - `cafe = 0.8`
    - `museum = 0.3`

- **미술관 제약**
  - `"미술관은 하루 1개만"`, `"박물관 하루 2개만"` 등:
    - 정규식으로 숫자 추출 → `constraints.museum_per_day = 그 숫자`

- **출력 옵션 / clarify**
  - `include_map`, `include_excel`, `include_cost`는 항상 `true`로 강제
  - `clarify.needed`: 누락 필드가 하나라도 있으면 `true`
  - `clarify.missing_fields`: 누락된 필드 경로 배열 (현재 필수 기준: `dates.days`)

---

## 예시 요청

### 1. 기본 기간/도시

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "파리 3박 4일 일정 만들어줘"}'
```

### 2. 자유여행 기본값

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "파리 자유여행 계획 세워줘"}'
```

### 3. 숙소 + 기간

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "숙소는 에펠탑 근처고 2박 3일로 짜줘"}'
```

### 4. 취향 + 제약

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "카페 많이, 미술관은 하루 1개만"}'
```

### 5. 이동 수단/최적화

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "대중교통 위주로, 환승 적게"}'
```

위 예시들은 모두 **동일한 CREATE_PLAN 스키마 구조**를 유지하며,  
필드가 비어 있는 경우에는 `null` 또는 기본값이 자동으로 채워집니다.

