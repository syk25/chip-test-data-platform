# ADR-007: Redis 이중 역할 — 캐시 + Pub/Sub 실시간 이벤트

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

채용공고 합류 직후 담당업무에 **"Redis Pub/Sub을 활용한 실시간 데이터 전송 시스템 개발"** 이
명시되어 있다. 기존 설계에서 Redis는 캐시(Cache-Aside) 용도로만 계획됐으나,
Pub/Sub 실시간 이벤트 기능을 추가한다.

## 결정

Redis를 **캐시 + Pub/Sub** 두 가지 용도로 함께 사용한다.
같은 Redis 인스턴스, 다른 키 네임스페이스로 역할을 분리한다.

### 역할 분리

| 역할 | 패턴 | 예시 |
|---|---|---|
| 캐시 | `cache:{resource}:{id}` | `cache:lot:42:summary` |
| Pub/Sub 채널 | `events:{scope}` | `events:global`, `events:lot:42` |

### 발행하는 이벤트 2종

```json
// 1. STDF 파싱 완료
{
  "type": "stdf.parsed",
  "lot_id": 42,
  "file_id": 7,
  "status": "success",
  "timestamp": "2026-05-05T10:00:00Z"
}

// 2. FAIL률 임계치 초과 (기본 임계치: 10%)
{
  "type": "lot.fail_rate_exceeded",
  "lot_id": 42,
  "fail_rate": 0.152,
  "threshold": 0.10,
  "timestamp": "2026-05-05T10:01:00Z"
}
```

### 클라이언트 전달 방식: SSE (Server-Sent Events)

WebSocket 대신 SSE를 선택한 이유:
- 서버→클라이언트 단방향 알림이므로 SSE로 충분
- 브라우저 기본 API (`EventSource`)로 바로 연결 가능
- FastAPI `StreamingResponse`로 구현, 추가 라이브러리 불필요
- HTTP/2 기반 — 기존 nginx 설정 그대로 사용

```
GET /api/v1/events          # 전체 알림 스트림 (JWT 필요)
```

### 흐름

```
Worker: STDF 파싱 완료
    ↓
redis.publish("events:global", json)
    ↓
FastAPI SSE 엔드포인트가 subscribe 중
    ↓
StreamingResponse로 클라이언트에 전달
    ↓
프론트엔드 EventSource가 수신 → UI 업데이트
```

## 구현 일정

- **Day 3** (STDF Worker): 파싱 완료 후 `redis.publish` 추가
- **Day 5** (조회 API): `GET /api/v1/events` SSE 엔드포인트 구현

## 결과

### 긍정적
- 채용공고 "Redis Pub/Sub 실시간 데이터 전송" 직접 구현으로 매칭
- Redis 한 인스턴스로 캐시·실시간 이벤트 모두 처리 — 운영 복잡도 최소
- SSE는 WebSocket보다 구현 단순, nginx 설정 변경 불필요
- 프론트엔드 대시보드가 파싱 완료 즉시 업데이트되는 UX 제공

### 부정적 / 트레이드오프
- SSE는 단방향 — 클라이언트→서버 메시지가 필요하면 WebSocket으로 교체 필요
- Redis 구독 연결이 클라이언트 수만큼 증가 (스케일 시 Redis Cluster 고려)
- 연결이 끊기면 클라이언트가 재연결해야 함 (EventSource는 자동 재연결 지원)

### 보류 / 운영 시점
- 이벤트 지속성: Redis Streams로 교체하면 이벤트 재생 가능
- 알림 채널 세분화: `events:lot:{id}`, `events:user:{id}` 등 구독 범위 축소
- FAIL률 임계치를 DB에서 사용자 설정 가능하게 확장
