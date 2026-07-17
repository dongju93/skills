# 제6절 캡슐화 — 2026 재구성

이 파일은 KISA 「Python 시큐어코딩 가이드」(2023)의 제6절을 2026년 7월 기준으로 교체한 정본이다. 배열뿐 아니라 모든 가변 객체와 요청·사용자·tenant·task 사이 상태 격리를 포함한다.

## 목차

1. 잘못된 세션·공유 상태에 의한 정보 노출
2. 제거되지 않고 남은 디버그 코드
3. Public 메소드에서 반환된 Private 가변 객체
4. Private 가변 객체에 Public 데이터 할당

## 1. 잘못된 세션·공유 상태에 의한 정보 노출 (CWE-362, CWE-488)

module global, class variable, singleton, 재사용 worker와 cache에 요청별 데이터를 저장하면 다른 사용자·tenant의 응답에 섞이거나 경쟁조건이 발생할 수 있다.

### 우선 확인

- 클래스 변수나 module global에 현재 사용자·요청·토큰을 저장하는 코드
- mutable default argument와 process-local cache
- async task·thread·greenlet 사이 context 전파
- tenant가 cache key, connection state, temporary path에서 누락된 코드
- object pool에 반환하기 전 상태를 초기화하지 않는 코드

### 안전한 코딩기법

- 요청 상태는 함수 인자, 요청 객체 또는 수명이 명확한 context에 둔다.
- cache·temporary object·idempotency key에 사용자·tenant·권한 범위를 포함한다.
- `contextvars`를 사용할 때 task 생성과 background execution의 context 복사 범위를 확인한다.
- connection·serializer·client 재사용 객체에 사용자 데이터를 남기지 않는다.
- process-local lock·cache가 다중 worker·host에서 전역 일관성을 제공한다고 가정하지 않는다.

동시에 다른 tenant의 요청을 반복하고 worker·connection 재사용 후 데이터 혼합을 테스트한다.

## 2. 제거되지 않고 남은 디버그 코드 (CWE-489)

debug endpoint, interactive debugger, test bypass, 임시 관리자 계정, `breakpoint()`, verbose trace와 feature flag가 운영에 남으면 인증 우회·코드 실행·정보 노출로 이어질 수 있다.

### 안전한 코딩기법

- 운영 build·설정에서 debugger와 debug route를 제거한다.
- `DEBUG`, `TESTING`, bypass header와 hidden query parameter를 코드·설정·배포 manifest에서 검색한다.
- debug 기능이 필요하면 별도 관리 plane, 강한 인증, 네트워크 제한과 감사 로그를 적용한다.
- assertion을 보안 검증에 사용하지 않는다. 최적화 모드에서 제거될 수 있다.
- test key·fixture account·개발 CA를 운영 이미지와 secret store에 포함하지 않는다.
- release pipeline에서 debug 설정과 알려진 표식을 검사한다.

운영과 동일한 아티팩트·환경변수로 직접 endpoint와 framework 기본 debugger를 확인한다.

## 3. Public 메소드에서 반환된 Private 가변 객체 (CWE-495)

내부 list·dict·set·bytearray 또는 중첩 객체의 참조를 그대로 반환하면 호출자가 검증·불변식·권한 경계를 우회해 상태를 변경할 수 있다.

### 안전한 코딩기법

- 불변 tuple, `frozenset`, read-only view 또는 필요한 필드만 담은 immutable DTO를 반환한다.
- 복사본이 필요하면 중첩 구조와 포함 객체까지 threat model에 맞는 깊이로 복사한다.
- 민감 필드와 내부 식별자를 반환 모델에서 제외한다.
- ORM object·Pydantic model·dataclass가 내부 mutable field를 공유하는지 확인한다.
- 반환 후 내부 상태가 변경되거나 호출자의 변경이 내부에 반영되는지 테스트한다.

```python
def allowed_scopes(self) -> tuple[str, ...]:
    return tuple(self._allowed_scopes)
```

얕은 복사만으로 중첩 가변 객체가 격리된다고 가정하지 않는다.

## 4. Private 가변 객체에 Public 데이터 할당 (CWE-496)

외부에서 받은 list·dict·객체 참조를 내부 필드에 그대로 저장하면 호출자가 나중에 원본을 변경해 검증된 상태를 우회할 수 있다.

### 안전한 코딩기법

- 입력을 검증한 뒤 필요한 필드만 새 내부 객체로 구성한다.
- 단순 값은 immutable representation으로 정규화한다.
- 복사가 필요하면 중첩 객체, custom class와 파일·socket 같은 capability를 고려한다.
- mutable default argument를 사용하지 않는다.
- setter 이후 호출자가 원본을 변경해도 내부 invariant가 유지되는지 테스트한다.

```python
class Policy:
    def __init__(self, scopes: list[str]) -> None:
        validated = [validate_scope(scope) for scope in scopes]
        self._scopes = tuple(validated)
```

## 검증 체크리스트

- [ ] 요청·사용자·tenant별 상태가 process·thread·task 재사용에서 분리되는지 확인한다.
- [ ] cache key와 temporary resource에 필요한 보안 범위가 포함되는지 확인한다.
- [ ] 운영 아티팩트에 debugger·bypass·test secret이 없는지 확인한다.
- [ ] 반환값·입력 원본을 변경해도 내부 상태가 변하지 않는지 확인한다.
- [ ] 얕은 복사와 중첩 가변 객체의 aliasing을 테스트한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [Python contextvars](https://docs.python.org/3.14/library/contextvars.html)
- [Python copy semantics](https://docs.python.org/3.14/library/copy.html)
- [Python data model](https://docs.python.org/3.14/reference/datamodel.html)
