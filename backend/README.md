# MileDay Backend

FastAPI 기반의 MileDay 백엔드 REST API 서버입니다.

---

## 🛠️ 기술 스택

- **Framework**: Python 3.11+, FastAPI, Uvicorn
- **Validation**: Pydantic v2
- **Database / Auth**: Supabase PostgreSQL, Supabase Auth
- **Testing**: Pytest, Pytest-cov

---

## 🚀 개발 및 실행

### 가상환경 설정 및 의존성 설치
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 환경 변수 설정
`.env.example`을 복사하여 `.env`를 생성하고 Supabase 연결 정보를 입력합니다:
```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

### 서버 실행
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 📂 아키텍처 및 디렉터리 구조

- `app/api/routers/`: Auth, Goals, Milestones, Calendar, Settings 등의 엔드포인트 라우터
- `app/services/`: 비즈니스 로직, 데이터 가공 및 권한 검증
- `app/repositories/`: Supabase PostgreSQL DB 접근 및 쿼리 처리
- `app/schemas/`: Pydantic 요청/응답 스키마
- `app/core/`: 설정(`config.py`), 로깅(`logging.py`), 미들웨어(`middleware.py`), Supabase 클라이언트(`supabase.py`)
- `app/exceptions/`: 계층별 Custom Exception 및 글로벌 에러 핸들러
