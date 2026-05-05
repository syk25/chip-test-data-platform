FROM python:3.12-slim

# uv 바이너리 복사 (별도 설치 불필요)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 레이어 캐시 최적화: 소스 복사 전 락 파일 먼저
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# venv 바이너리를 PATH에 추가 (docker-compose command 오버라이드 시 uvicorn/python 직접 사용 가능)
ENV PATH="/app/.venv/bin:$PATH"

# 애플리케이션 소스
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# api: docker-compose에서 command로 오버라이드
# worker: docker-compose에서 command로 오버라이드
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
