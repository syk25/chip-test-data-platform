# ADR-001: 비동기 STDF 처리 — RabbitMQ 메시지 큐 도입

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

OSAT(외주 테스트 업체)는 검사 완료 즉시 STDF 파일을 자동으로 업로드한다.
파일 1개당 파싱·파티셔닝·DB 삽입에 수십 초가 소요되며, 동시에 여러 OSAT에서
업로드가 몰릴 수 있다.

동기 처리 방식의 문제:
- 클라이언트가 처리 완료까지 HTTP 연결을 유지해야 함 (수십 초 블로킹)
- 처리 실패 시 재시도 책임이 클라이언트에게 넘어감
- API 서버 부하가 파일 수에 비례해 선형으로 증가

## 결정

RabbitMQ 메시지 큐를 도입해 **수신(API)**과 **처리(Worker)**를 분리한다.

```
OSAT → POST /stdf-files → FastAPI (202 Accepted 즉시 응답)
                               ↓
                        RabbitMQ 큐에 작업 등록
                               ↓
                        Python Worker가 큐에서 소비
                               ↓
                        pystdf 파싱 → PostgreSQL 삽입
```

- API는 파일을 스토리지에 저장하고 큐에 메시지만 넣은 뒤 **202 Accepted** 즉시 반환
- Worker는 독립 프로세스로 큐에서 작업을 하나씩 꺼내 처리
- 처리 결과는 `file_processing_jobs` 테이블에 기록 (클라이언트가 polling 가능)

## 결과

### 긍정적
- API 응답 시간이 파일 크기와 무관하게 일정 (수 ms 수준)
- Worker를 수평 확장(`docker compose up --scale worker=N`)하면 처리량 선형 증가
- Worker 실패 시 메시지가 큐에 남아 자동 재처리 가능 (at-least-once 보장)
- API 서버와 Worker가 독립적으로 장애 격리

### 부정적 / 트레이드오프
- 처리 결과를 즉시 알 수 없음 — 클라이언트가 `GET /stdf-files/{id}` polling 필요
- RabbitMQ 컨테이너가 추가됨 (운영 복잡도 소폭 증가)
- Kafka 대비 대규모 스트리밍 처리량은 낮음 (본 프로젝트 규모에서는 무관)

### Kafka 대신 RabbitMQ를 선택한 이유
- 본 시스템의 처리 단위는 "파일 1개" — 초당 수만 이벤트의 스트리밍이 아님
- RabbitMQ는 메시지 라우팅·우선순위 큐·Dead Letter Queue 기능이 기본 포함
- 학습 곡선이 낮아 6일 일정 내 안정적 구현 가능
- 향후 처리량이 Kafka 도입 기준에 도달하면 aio-pika → kafka-python 교체로 대응

### 보류 / 운영 시점
- Dead Letter Queue(DLQ) 설정 — 반복 실패 메시지 별도 보관
- Worker 수 자동 조정 (KEDA 등 오토스케일러)
- 처리 완료 시 WebSocket/SSE 푸시 알림 (현재는 polling)
