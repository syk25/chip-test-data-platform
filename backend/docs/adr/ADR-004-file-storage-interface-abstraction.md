# ADR-004: 파일 스토리지 인터페이스 추상화 (로컬 → S3 마이그레이션 경로 확보)

**상태**: Accepted  
**날짜**: 2026-05-05

---

## 컨텍스트

STDF 파일 원본을 어디에 저장할지 결정해야 한다.
운영 환경에서는 S3 같은 객체 스토리지가 표준이지만,
6일 프로젝트에서 AWS 설정·비용·보안 설정까지 포함하면 일정 위험이 크다.

## 결정

`app/storage/` 디렉토리에 **인터페이스 추상화 레이어**를 둔다.

```
app/storage/
├── interface.py   # StorageBackend 추상 클래스
├── local.py       # LocalStorage 구현체 (개발/데모용)
└── s3.py          # S3Storage 구현체 (껍데기 — 운영 시 구현)
```

`interface.py`가 정의하는 계약:
```python
class StorageBackend(ABC):
    async def save(self, file_id: str, data: bytes) -> str: ...
    async def load(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...
```

`pydantic-settings`의 `STORAGE_BACKEND` 환경 변수 하나로 구현체를 교체한다.
현재는 `LocalStorage`가 Docker named volume(`stdf_storage`)에 저장한다.

## 결과

### 긍정적
- 객체 스토리지 마이그레이션 시 `local.py` → `s3.py` 구현, 환경 변수 교체 — 1줄 변경
- 테스트에서 `MockStorage`를 주입 가능 — 실제 파일 시스템 없이 단위 테스트 가능
- API 서버·Worker 양쪽에서 동일 인터페이스로 파일 접근

### 부정적 / 트레이드오프
- 추상화 레이어 코드가 추가됨 (단, 3개 파일, 각 20~40줄 수준)
- 로컬 스토리지는 컨테이너 볼륨에 묶여 있어 다중 호스트 배포 시 공유 불가
  → 수평 확장 시 S3 구현체로 교체하면 해결

### 보류 / 운영 시점
- `s3.py` 구현 (boto3 또는 aiobotocore 사용)
- 파일 접근 URL 만료 시간 설정 (Presigned URL)
- 스토리지 백엔드별 비용/성능 비교 테스트
