# 제5절 코드오류

## 목차

1. None 역참조와 불명확한 반환 계약
2. 부적절한 자원 해제
3. 신뢰할 수 없는 데이터의 역직렬화

## 1. None 역참조와 불명확한 반환 계약 (CWE-476)

공격자가 조회 실패·누락 필드·예외 fallback을 유도해 `None`을 생성하고 코드가 이를 역참조하면 서비스 거부나 보안 검사 우회가 발생할 수 있다.

### 안전한 코딩기법

- 함수가 `None`을 반환할 수 있는지 타입과 문서로 명시한다.
- `if value:`와 `if value is None:`을 구분해 0·빈 문자열·빈 컬렉션을 오판하지 않는다.
- 권한·인증 객체 조회 실패는 명시적으로 거부한다.
- sentinel, Result 유형, 예외 또는 필수 반환처럼 도메인에 맞는 계약을 사용한다.
- optional chaining식 fallback이 보호 값을 느슨하게 만들지 않는지 확인한다.

```python
user = repository.find_user(user_id)
if user is None:
    raise NotFound
authorize(actor, user)
```

누락·삭제·경쟁조건·외부 API의 null 응답을 테스트한다.

## 2. 부적절한 자원 해제 (CWE-404, CWE-772)

파일, socket, DB connection, cursor, lock, subprocess, temporary directory와 async task가 예외·취소 경로에서 정리되지 않으면 자원 고갈과 deadlock이 발생한다.

### 안전한 코딩기법

- `with`·`async with`를 사용하고 직접 관리할 때 `try/finally`로 정리한다.
- connection pool과 client의 애플리케이션 수명주기를 명시한다.
- subprocess에 timeout을 두고 timeout 후 terminate·kill·wait 순서를 처리한다.
- async task의 참조, 오류 회수, cancellation과 shutdown을 관리한다.
- 임시 파일·디렉터리와 부분 생성 아티팩트를 실패 후 제거한다.
- lock 범위를 최소화하고 모든 경로에서 해제되도록 context manager를 사용한다.

```python
with open(path, "rb") as source:
    return process_stream(source, max_bytes=MAX_BYTES)
```

성공 경로뿐 아니라 parser 오류, timeout, cancellation, client disconnect와 worker shutdown을 테스트한다.

## 3. 신뢰할 수 없는 데이터의 역직렬화 (CWE-502)

`pickle`, `shelve`, `marshal`, 객체 태그를 허용한 YAML과 일부 프레임워크 serializer는 로드 과정에서 코드 실행이나 임의 객체 생성을 일으킬 수 있다.

### 안전한 코딩기법

- 비신뢰 경계에는 JSON 같은 데이터 전용 형식과 명시적 스키마를 사용한다.
- 허용 필드, 타입, 문자열 길이, 항목 수, 숫자 범위와 중첩 깊이를 검증한다.
- unknown·extra field 처리 정책을 명시한다.
- `pickle`·`shelve`·Python 객체 YAML을 캐시·쿠키·큐·업로드·DB blob에 사용하지 않는다.
- YAML이 필요하면 객체 생성 기능이 없는 safe loader를 사용하고 입력 예산을 적용한다.
- producer와 consumer 버전, schema migration과 호환 실패 동작을 관리한다.

HMAC은 데이터가 키 보유자에게서 왔음을 일부 확인할 뿐 역직렬화 과정의 코드 실행 능력을 제거하지 않는다. producer·키·저장소 침해와 과도한 권한도 남으므로, HMAC 확인 후 `pickle.loads()`를 일반적인 안전 예제로 인정하지 않는다.

레거시 pickle이 불가피하면 producer 격리, 키 분리, 최소 권한, 클래스 허용 목록, 크기 제한, 격리된 consumer와 데이터 형식 전환 계획을 함께 둔다.

## 검증 체크리스트

- [ ] 누락·null·빈 값이 인증·인가 fallback을 만들지 않는지 확인한다.
- [ ] 예외·timeout·취소 후 열린 파일·연결·task·lock이 남지 않는지 측정한다.
- [ ] 외부 데이터 형식이 객체 생성 기능을 갖지 않는지 확인한다.
- [ ] schema가 타입뿐 아니라 크기·개수·깊이와 extra field를 제한하는지 확인한다.
- [ ] 조작·대형·깊은 payload가 안전하게 거부되는지 테스트한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [Python pickle security warning](https://docs.python.org/3.14/library/pickle.html)
- [Python context manager types](https://docs.python.org/3.14/library/contextlib.html)
- [OWASP Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html)
