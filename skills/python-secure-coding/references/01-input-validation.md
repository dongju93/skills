# 제1절 입력데이터 검증 및 표현

## 목차

1. SQL 삽입
2. 코드 삽입
3. 경로 조작 및 자원 삽입
4. 크로스사이트 스크립트(XSS)
5. 운영체제 명령어 삽입
6. 위험한 형식 파일 업로드와 압축 해제
7. 신뢰되지 않은 URL로 자동접속 연결
8. 부적절한 XML 외부 개체 참조
9. XML 삽입
10. LDAP 삽입
11. 크로스사이트 요청 위조(CSRF)
12. 서버사이드 요청 위조(SSRF)
13. HTTP 응답분할과 로그 위조
14. 정수·크기·자원 계산 오류
15. 보안기능 결정에 사용되는 부적절한 입력값
16. 포맷 스트링 삽입
17. 현대 Python 추가 점검

## 공통 판정 원칙

- HTTP·WebSocket·CLI·파일·큐·DB·환경변수·외부 API 응답·모델 출력을 신뢰 경계별로 구분한다.
- 공격자 통제 값이 위험 동작에 도달하는 실제 소스-싱크 흐름을 확인한다. 위험한 함수 이름만으로 취약점을 확정하지 않는다.
- 구문 검증, 의미 검증, 권한 검증, 출력 인코딩을 구분한다. 하나의 검증으로 다른 경계를 대신하지 않는다.
- 입력 바이트 수, 컬렉션 크기, 중첩 깊이, 처리 시간, 메모리·디스크 사용량을 제한한다.
- 검증 실패 시 보호 기능을 우회하는 값으로 계속 실행하지 말고 거부한다.

## 1. SQL 삽입 (CWE-89)

외부 입력을 SQL 문자열의 구조에 결합하면 조건 우회, 데이터 노출·변경 또는 DB 기능 악용이 가능하다.

### 안전한 코딩기법

- DB-API placeholder, ORM lookup 또는 SQLAlchemy bind parameter를 사용한다.
- 테이블명·열명·정렬 방향처럼 바인딩할 수 없는 식별자는 서버가 정의한 허용 목록에 매핑한다.
- `raw()`, `extra()`, `text()`, 저장 프로시저 내부 동적 SQL까지 확인한다.
- DB 계정에는 필요한 스키마·연산 권한만 부여한다.

```python
SORT_COLUMNS = {"created": "created_at", "name": "display_name"}
sort_column = SORT_COLUMNS.get(requested_sort)
if sort_column is None:
    raise ValueError("unsupported sort")

cursor.execute(
    f"SELECT id, display_name FROM users WHERE tenant_id = %s ORDER BY {sort_column}",
    [tenant_id],
)
```

식별자만 엄격히 매핑하고 데이터 값은 반드시 바인딩한다. 악성 따옴표, 주석, 다중문과 권한 없는 tenant 값으로 회귀 테스트한다.

## 2. 코드 삽입 (CWE-94, CWE-95)

외부 입력이나 모델 출력을 `eval`, `exec`, `compile`, 동적 import에 전달하면 임의 코드 실행으로 이어질 수 있다.

### 안전한 코딩기법

- 문자열을 코드로 실행하지 말고 허용된 동작을 함수 객체에 직접 매핑한다.
- 표현식이 필요하면 작은 문법의 전용 파서를 사용하고 연산 종류·입력 크기·깊이·실행 시간을 제한한다.
- `isalnum()` 또는 정규식 검사를 통과시킨 뒤 `eval()`하는 방식을 안전하다고 보지 않는다.
- `ast.literal_eval()`도 대형·깊은 입력에 의한 자원 고갈 가능성을 제한한다.

```python
ACTIONS = {"friends": get_friends_list, "address": get_address}
action = ACTIONS.get(requested_action)
if action is None:
    raise ValueError("unsupported action")
result = action()
```

## 3. 경로 조작 및 자원 삽입 (CWE-22, CWE-23, CWE-99)

외부 입력으로 파일·디렉터리·소켓·장치 같은 자원을 선택하면 기준 경로 이탈, 심볼릭 링크 우회, 임의 파일 접근 또는 자원 충돌이 발생할 수 있다.

### 안전한 코딩기법

- 가능하면 외부 식별자를 서버 측 경로에 매핑한다.
- 경로를 받아야 하면 기준 디렉터리와 후보를 정규화하고 포함 관계를 확인한다.
- 공격자가 쓰기 가능한 디렉터리를 기준 경로로 사용하지 않는다.
- 예측 가능한 임시 이름 대신 `tempfile`을 사용한다.
- 민감한 생성·교체에는 `dir_fd`, `O_NOFOLLOW`, 배타적 생성과 원자적 교체를 검토한다.
- `exists()` 후 `open()`하는 검사-사용 구조보다 작업 자체의 예외를 처리한다.

```python
from pathlib import Path

BASE = Path("/srv/app/data").resolve()
candidate = (BASE / user_name).resolve()
if not candidate.is_relative_to(BASE):
    raise ValueError("path escapes base directory")
```

POSIX·Windows 구분자, 절대 경로, 인코딩, 심볼릭 링크와 동시 교체를 테스트한다.

## 4. 크로스사이트 스크립트(XSS) (CWE-79)

공격자 입력이 HTML·속성·JavaScript·CSS·URL 문맥에 맞는 인코딩 없이 출력되면 브라우저에서 스크립트가 실행될 수 있다.

### 안전한 코딩기법

- Django·Jinja의 자동 이스케이프를 유지한다.
- `mark_safe`, `|safe`, `autoescape off`, 문자열 HTML 조립을 우선 추적한다.
- HTML, 속성, JavaScript, CSS, URL 문맥에 맞는 인코딩을 사용한다.
- 제한된 HTML을 허용해야 하면 검증된 sanitizer와 태그·속성·URL scheme 허용 목록을 사용한다.
- CSP는 보조 방어로 사용하고 출력 인코딩을 대체하지 않는다.

저장형·반사형 입력과 DOM sink, JSON을 `<script>`에 삽입하는 경로를 함께 확인한다.

## 5. 운영체제 명령어 삽입 (CWE-78)

외부 입력이 셸 명령 문자열에 결합되면 명령 구분자, 치환, 리다이렉션 등을 통해 임의 명령이 실행될 수 있다.

### 안전한 코딩기법

- 파일·압축·네트워크 작업은 Python API로 수행한다.
- subprocess가 필요하면 인자 배열을 사용하고 `shell=False`를 유지한다.
- 실행 파일을 절대 경로 또는 신뢰된 고정 경로로 선택하고 환경변수·작업 디렉터리·권한을 제한한다.
- 허용 가능한 값은 서버 측 목록에 매핑하고 timeout·출력 크기를 제한한다.

```python
subprocess.run(
    ["/usr/bin/convert", source_path, destination_path],
    shell=False,
    check=True,
    timeout=10,
    env={"PATH": "/usr/bin:/bin"},
)
```

인자 배열은 대상 프로그램 자체의 옵션 삽입을 자동으로 막지 않는다. `--` 지원 여부와 인자 의미도 검증한다.

## 6. 위험한 형식 파일 업로드와 압축 해제 (CWE-434, CWE-409)

파일명·확장자만 신뢰하거나 웹 루트에 실행 가능한 파일을 저장하면 코드 실행, 저장형 XSS, 악성 콘텐츠 배포와 자원 고갈이 가능하다.

### 안전한 코딩기법

- 허용 확장자와 실제 콘텐츠 형식을 함께 확인한다.
- 애플리케이션이 만든 무작위 이름으로 웹 루트 밖의 비실행 저장소에 보관한다.
- 업로드 크기·개수, 이미지 픽셀 수, 문서 중첩과 처리 시간을 제한한다.
- 필요하면 악성코드와 문서 active content를 검사한다.
- 다운로드 시 안전한 `Content-Type`과 `Content-Disposition`을 명시한다.

압축 파일은 멤버 수, 총 비압축 크기, 압축률, 경로 길이, 링크·특수 파일을 추출 전에 검사한다. 새 임시 디렉터리에 추출하고 모든 대상 경로가 기준 디렉터리 안인지 확인한다. TAR는 지원 버전에서 `filter="data"`를 명시하되 이것만으로 압축 폭탄을 막는다고 가정하지 않는다. 기능이 없는 버전에서 `fully_trusted`로 조용히 후퇴하지 않는다.

## 7. 신뢰되지 않은 URL로 자동접속 연결 (CWE-601)

외부 입력을 redirect 대상으로 그대로 사용하면 피싱, 토큰 유출 또는 신뢰 도메인 우회가 가능하다.

### 안전한 코딩기법

- 상대 경로 또는 서버가 정의한 목적지 ID를 사용한다.
- 외부 URL이 필요하면 표준 파서로 scheme·host·port·userinfo를 분리하고 정확한 허용 목록과 비교한다.
- `//evil.example`, userinfo, 역슬래시, 다중 인코딩과 국제화 도메인 우회를 테스트한다.
- 프레임워크의 안전 URL 판별 API를 사용하되 허용 host·scheme을 명시한다.

## 8. 부적절한 XML 외부 개체 참조 (CWE-611, CWE-776)

외부 XML의 DTD·외부 엔티티·XInclude·네트워크 접근은 파일 노출, SSRF, entity expansion과 메모리 고갈을 일으킬 수 있다.

### 안전한 코딩기법

- XML이 불필요하면 데이터 전용 형식을 사용한다.
- DTD, 외부 엔티티, XInclude와 네트워크 접근을 끈 파서를 선택한다.
- 실제 Python·라이브러리·Expat 버전과 파서 옵션을 확인한다.
- 입력 크기, 요소 수, 깊이, 토큰 크기와 처리 시간을 제한한다.
- 보안 래퍼 사용만으로 안전하다고 단정하지 않고 의존성 버전을 유지한다.

## 9. XML 삽입 (CWE-643)

외부 입력을 XPath·XQuery·XML 문자열 구조에 결합하면 쿼리 의미나 문서 구조가 변조될 수 있다.

### 안전한 코딩기법

- XPath 변수 바인딩 또는 라이브러리의 안전한 노드 생성 API를 사용한다.
- 태그·속성 이름처럼 바인딩할 수 없는 구조 요소는 허용 목록에 매핑한다.
- 문자열 연결로 XML을 만들지 말고 Element API를 사용한다.
- namespace, 인코딩, 대형 결과 집합을 제한한다.

## 10. LDAP 삽입 (CWE-90)

외부 입력을 LDAP filter 또는 DN에 결합하면 인증 우회와 디렉터리 정보 노출이 가능하다.

### 안전한 코딩기법

- filter 값과 DN 값에 각각 맞는 라이브러리 escape 함수를 사용한다.
- 검색 base와 scope를 고정하고 반환 속성·개수·시간을 제한한다.
- 디렉터리 계정에 최소 권한을 부여한다.
- `*`, 괄호, NUL과 DN 구분자를 포함한 입력을 테스트한다.

## 11. 크로스사이트 요청 위조(CSRF) (CWE-352)

브라우저가 자동 전송하는 쿠키 인증을 사용하는 상태 변경 요청에 요청 출처 검증이 없으면 공격자가 사용자의 권한으로 동작을 수행할 수 있다.

### 안전한 코딩기법

- 프레임워크 CSRF 미들웨어와 토큰 검증을 유지하고 `csrf_exempt` 사용을 최소화한다.
- 상태 변경을 GET으로 제공하지 않는다.
- `SameSite` 쿠키, Origin·Referer 검사를 보조 방어로 사용한다.
- CORS 허용과 CSRF 방어를 혼동하지 않는다.
- 민감 작업에는 재인증 또는 transaction-specific authorization을 적용한다.

Bearer token을 명시적 헤더로 보내는 API도 XSS, 토큰 저장 위치와 CORS 정책을 별도로 검토한다.

## 12. 서버사이드 요청 위조(SSRF) (CWE-918)

서버가 외부 입력으로 지정된 URL에 요청하면 내부망, 클라우드 메타데이터, 관리 서비스 또는 로컬 파일에 접근할 수 있다.

### 안전한 코딩기법

1. URL 대신 서버 측 식별자를 고정 대상에 매핑한다.
2. URL이 필요하면 scheme·host·port·userinfo를 파싱하고 필요한 scheme과 포트만 허용한다.
3. A·AAAA의 모든 결과에서 loopback, private, link-local, multicast, reserved, unspecified와 조직 금지 대역을 차단한다.
4. 검증한 주소와 실제 연결 대상을 일치시켜 DNS rebinding과 검사-사용 경쟁을 줄인다.
5. redirect를 끄거나 매 단계 같은 검증을 반복한다.
6. connect/read timeout과 최대 응답 크기를 제한한다.
7. egress 정책으로 메타데이터·내부망·관리망을 차단한다.

단일 `is_global` 검사나 최초 DNS 결과만으로 정책이 충족된다고 가정하지 않는다.

## 13. HTTP 응답분할과 로그 위조 (CWE-113, CWE-117)

외부 입력의 CR/LF가 응답 헤더나 텍스트 로그에 들어가면 헤더 삽입, 캐시 오염 또는 감사 기록 위조가 가능하다.

### 안전한 코딩기법

- 응답 헤더는 프레임워크 API로 설정하고 개행·제어 문자를 거부한다.
- 파일명은 `Content-Disposition` 전용 인코딩 API를 사용한다.
- 구조화 로깅을 사용하고 외부 문자열의 제어 문자를 경계에서 처리한다.
- 토큰·쿠키·비밀번호·전체 요청 본문을 로그에 남기지 않는다.

## 14. 정수·크기·자원 계산 오류 (CWE-190, CWE-400, CWE-770)

Python 정수는 일반적으로 고정 폭 오버플로우가 없지만 C 확장·바이너리 포맷·DB 타입 경계, 음수와 과도한 크기 계산은 예외, 메모리 고갈과 서비스 거부를 일으킬 수 있다.

### 안전한 코딩기법

- 길이·개수·오프셋·곱셈 결과에 명시적 상한과 하한을 둔다.
- 할당·압축 해제·반복 전에 누적 크기를 검증한다.
- C API·NumPy·struct·DB 타입으로 변환할 때 대상 범위를 확인한다.
- 요청, 파싱, 정규식, 이미지·문서 처리에 시간·메모리 예산을 적용한다.

## 15. 보안기능 결정에 사용되는 부적절한 입력값 (CWE-807)

클라이언트가 보낸 role, owner, price, tenant, 인증 상태나 프록시 헤더를 신뢰하면 권한 우회가 발생한다.

### 안전한 코딩기법

- 권한과 소유권은 서버 측 인증 컨텍스트와 신뢰된 데이터 저장소에서 얻는다.
- reverse proxy 헤더는 신뢰 프록시가 덮어쓰도록 구성하고 직접 도달 경로를 막는다.
- 요청 데이터를 모델에 통째로 적용하지 말고 변경 가능한 필드만 명시한다.
- 모델·에이전트 출력도 권한을 부여하는 근거로 사용하지 않는다.

## 16. 포맷 스트링 삽입 (CWE-134)

외부 입력을 포맷 문자열 자체로 사용하면 예외, 정보 노출, 로그 변조 또는 예상치 못한 객체 접근이 발생할 수 있다.

### 안전한 코딩기법

- 포맷 문자열은 코드에 고정하고 외부 입력은 값으로만 전달한다.
- 로깅 API에서는 `logger.info("user=%s", user_name)`처럼 메시지 템플릿을 고정한다.
- 번역 문자열과 사용자 정의 템플릿에 허용 placeholder와 출력 길이를 제한한다.

## 17. 현대 Python 추가 점검

### 서버사이드 템플릿 삽입 (CWE-1336)

입력을 템플릿 컨텍스트 값으로 전달하는 것과 템플릿 소스로 컴파일하는 것을 구분한다. `render_template_string(user_input)`, `Template(user_input)`, 사용자 정의 filter·global과 동적 sandbox 설정을 우선 추적한다. sandbox를 완전한 격리 경계로 보지 않는다.

### 정규식 서비스 거부 (CWE-1333)

사용자가 정규식 자체를 제공하지 못하게 하고 입력 길이를 먼저 제한한다. 중첩 수량자와 모호한 대안을 검토하며 필요하면 시간 제한 가능한 엔진이나 별도 프로세스를 사용한다. 최악 입력으로 처리 시간을 검증한다.

### 대량 할당 (CWE-915)

`Model(**request.json)`, 반복 `setattr`, ORM bulk update에서 `role`, `owner_id`, `is_admin`, `price`, `tenant_id`, 상태 필드가 바뀌는지 확인한다. 입력 모델과 저장 모델을 분리하고 허용 필드 및 extra field 정책을 명시한다.

### AI·에이전트 입력

LLM 입력·검색 문서·모델 출력은 비신뢰 데이터로 취급한다. 모델 출력이 SQL·셸·파일 경로·URL·템플릿·패키지명에 직접 연결되지 않게 하고, 모든 도구 호출에서 typed schema, 대상 범위와 실행 주체의 권한을 서버가 다시 검증한다.

## 검증 체크리스트

- [ ] 악성 입력이 실제 sink에 도달하는지 확인한다.
- [ ] 인자화·이스케이프·허용 목록이 올바른 문맥에 적용됐는지 확인한다.
- [ ] 경로, URL, redirect, XML, 압축 파일의 우회 입력을 테스트한다.
- [ ] 입력 크기·중첩·시간·메모리·출력 크기 제한을 테스트한다.
- [ ] 검증 실패와 timeout이 fail closed인지 확인한다.
- [ ] 권한 없는 사용자, 다른 owner·tenant와 모델 조작 입력을 테스트한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [Python 3.14 Security Considerations](https://docs.python.org/3.14/library/security_warnings.html)
- [Python 3.14 tarfile extraction filters](https://docs.python.org/3.14/library/tarfile.html#extraction-filters)
- [Python 3.14 XML security](https://docs.python.org/3.14/library/xml.html#xml-vulnerabilities)
- [Python subprocess security considerations](https://docs.python.org/3.14/library/subprocess.html#security-considerations)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
