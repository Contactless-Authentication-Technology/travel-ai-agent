# Travel AI Agent

AI 기반 여행 예약 보조 시스템입니다.

## 구현 기능

### 여행 요청 파싱
- 한국어 자연어 입력 → 구조화된 여행 정보 추출 (LLM + regex fallback)

### 항공편 검색 (Kiwi.com API)
- 왕복/편도 항공편 검색 및 가격 비교
- 날짜별 최저가 캘린더
- Kiwi.com 예약 페이지 직접 연결

### 호텔 검색 (Booking.com API)
- 목적지 기반 호텔 목록 조회
- 호텔 사진, 평점, 가격 표시
- 객실 옵션 및 조식/무료취소 여부 확인
- Booking.com 페이지 직접 연결

### Chrome Extension
- Booking.com 최종 결제 단계 보조

## Structure
- `booking-agent/api` — FastAPI 대시보드 서버
- `booking-agent/core` — 파서, API 클라이언트 (Kiwi, Booking.com)
- `extension` — Chrome Extension (브라우저 자동화)
- `ai parser` — LLM 기반 여행 요청 파서
