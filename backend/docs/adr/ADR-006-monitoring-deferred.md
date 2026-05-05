# ADR-006: 모니터링 보류 — FastAPI 자동 메트릭 + 운영 시 Prometheus/Grafana

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

운영 환경의 백엔드 시스템에는 메트릭 수집·시각화가 필수다.
Prometheus + Grafana 스택이 Python 백엔드의 표준 선택이며,
`prometheus-client` 라이브러리로 FastAPI에 연동할 수 있다.

그러나 Prometheus + Grafana 컨테이너 추가·대시보드 설정·알림 규칙 정의까지
최소 1~2일이 소요되며, 이는 Day 1~5 핵심 기능 구현과 직접 충돌한다.

## 결정

모니터링 스택 구현을 **운영 시점으로 보류**한다.

대신 두 가지 기반을 지금 깔아둔다:

1. **FastAPI 자동 메트릭**: FastAPI는 `/docs` (OpenAPI), `/redoc` 엔드포인트를 자동 제공한다.
   `prometheus-client`를 추가하면 `/metrics` 엔드포인트를 1줄로 노출할 수 있다.
   ```python
   # 운영 시 추가할 코드 (1줄)
   from prometheus_fastapi_instrumentator import Instrumentator
   Instrumentator().instrument(app).expose(app)
   ```

2. **structlog 구조화 로깅**: 현재 구현에서 `structlog`로 JSON 형식 로그를 출력한다.
   이 로그는 ELK Stack 또는 CloudWatch Logs로 즉시 수집 가능하다.

## 결과

### 긍정적 (현재)
- 핵심 기능(STDF 처리, JWT/RBAC, 조회 API) 구현에 집중
- structlog JSON 로그만으로도 기본 운영 가시성 확보

### 부정적 / 트레이드오프
- CPU·메모리·처리량·응답시간 시각화 불가
- 알림(Alert) 자동화 불가
- 면접 질문 *"운영 모니터링은?"* 에 "미구현"이 아닌 "계획된 다음 단계"로 답해야 함

### 면접 방어 답변
> *"현재 구현에서는 structlog로 JSON 구조화 로그를 출력합니다.
> 운영 환경에서는 prometheus-fastapi-instrumentator 라이브러리를 추가하면
> /metrics 엔드포인트가 1줄로 노출되고, Grafana 대시보드와 연결할 수 있습니다.
> 6일 일정에서 모니터링 대시보드 설정보다 핵심 비즈니스 로직 완성을 우선했습니다."*

### 보류 / 운영 시점
- `prometheus-client` + `prometheus-fastapi-instrumentator` 추가
- Grafana 대시보드: 요청 수, 응답 시간 분포, Worker 처리 대기열 길이
- RabbitMQ 관리 UI (포트 15672) → Prometheus exporter 연결
- PostgreSQL exporter (`postgres_exporter`) 추가
