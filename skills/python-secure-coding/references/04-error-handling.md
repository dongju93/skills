# 제4절 에러처리 — 2026 재구성

이 파일은 KISA 「Python 시큐어코딩 가이드」(2023)의 제4절을 2026년 7월 기준으로 교체한 정본이다. 사용자 오류 응답뿐 아니라 fail-open, 민감 로그, 탐지·경보와 복구 가능성을 포함한다.

## 목차

1. 오류 메시지 정보노출
2. 오류상황 대응 부재
3. 부적절한 예외 처리
4. 보안 로깅과 관측

## 1. 오류 메시지 정보노출 (CWE-209)

traceback, SQL, 파일 경로, 설정, 토큰 또는 사용자 존재 여부가 응답에 포함되면 공격 정찰과 민감정보 노출로 이어질 수 있다.

### 안전한 코딩기법

- 사용자에게 안정된 오류 코드와 필요한 최소 설명만 제공한다.
- 상세 원인은 접근 통제된 서버 로그에 correlation ID와 함께 기록한다.
- 운영에서 Django `DEBUG`, Flask debugger와 대화형 exception page를 끈다.
- 인증·복구 응답은 계정 존재, MFA 등록, 잠금 여부를 불필요하게 구분하지 않는다.
- reverse proxy, ASGI/WSGI server, background worker의 기본 오류 페이지도 확인한다.

예상 오류와 예상하지 못한 오류를 테스트해 response body·header·trace에 비밀과 내부 구조가 없는지 확인한다.

## 2. 오류상황 대응 부재 (CWE-390)

인증서·서명·인가·파싱·무결성 검증 실패를 무시하거나 기본 허용으로 계속 실행하면 보안 통제가 우회된다.

### 안전한 코딩기법

- 보안 결정 오류는 fail closed로 처리한다.
- 실패 후 partial write, 임시 권한, lock, 파일과 세션을 정리한다.
- 복구 가능한 오류와 영구 오류를 구분하고 무제한 재시도를 피한다.
- 트랜잭션 rollback과 외부 side effect의 보상·멱등성을 설계한다.
- 중요한 검증 실패를 메트릭·경보·incident 절차에 연결한다.

```python
try:
    claims = verifier.verify(token)
except TokenVerificationError:
    logger.warning("token verification failed", extra={"request_id": request_id})
    raise Unauthorized
```

검증기 장애, key store timeout, 로그 저장 실패와 dependency 부분 장애 때의 동작을 확인한다.

## 3. 부적절한 예외 처리 (CWE-754)

광범위한 예외를 무조건 삼키거나 정상 결과로 바꾸면 데이터 손상과 보안 실패가 숨겨진다. 반대로 `except Exception` 자체만으로 취약하다고 단정하지 않는다.

### 안전한 코딩기법

- 복구 의미가 분명한 구체적 예외를 우선 처리한다.
- 경계 계층에서 광범위한 예외를 잡을 때 로그, rollback, 안전한 응답과 재발생 정책을 명시한다.
- `except: pass`, 빈 fallback, 성공 status 반환을 피한다.
- `BaseException`, `KeyboardInterrupt`, `SystemExit`, async cancellation을 부주의하게 삼키지 않는다.
- 예외 메시지 문자열을 프로그램 분기 조건으로 사용하지 않는다.
- cleanup은 `with`, `async with`, `try/finally`로 보장한다.

## 4. 보안 로깅과 관측 (CWE-117, CWE-223, CWE-532)

로그가 없으면 공격을 탐지·조사하기 어렵고, 과도한 로그는 비밀·개인정보를 노출하거나 로그 위조를 허용한다.

### 안전한 코딩기법

- 인증 실패, 권한 거부, 관리자 변경, 비밀 접근, 검증 실패와 비정상 트래픽을 구조화해 기록한다.
- 비밀번호, 토큰, 세션 쿠키, 키, 전체 요청 본문과 불필요한 개인정보를 기록하지 않는다.
- 외부 문자열의 CR/LF와 제어 문자를 구조화 로깅 경계에서 처리한다.
- timestamp, actor, action, target, result, request/correlation ID를 포함하되 위조 가능한 클라이언트 값과 구분한다.
- 로그 저장소의 접근, 보존, 무결성, 시간 동기화와 삭제 정책을 설정한다.
- 실패율·분산 로그인·권한 거부 급증에 임계값과 대응 책임자를 연결한다.

## 검증 체크리스트

- [ ] 운영 설정에서 상세 오류와 debugger가 비활성화됐는지 확인한다.
- [ ] 보안 검증·dependency 실패가 성공 경로로 전환되지 않는지 확인한다.
- [ ] 예외 후 transaction, lock, connection과 임시 자원이 정리되는지 확인한다.
- [ ] 로그에 필요한 보안 이벤트는 있고 비밀·개인정보는 없는지 확인한다.
- [ ] 경보가 실제 운영 채널에 도달하고 조사에 필요한 식별자가 연결되는지 확인한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [Python errors and exceptions](https://docs.python.org/3.14/tutorial/errors.html)
- [OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
