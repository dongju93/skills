# 제3절 시간 및 상태

## 목차

1. 경쟁조건과 검사시점·사용시점(TOCTOU)
2. 종료되지 않는 반복문·재귀와 자원 고갈
3. 비동기·취소·재시도 상태

## 1. 경쟁조건과 TOCTOU (CWE-362, CWE-367)

상태를 검사한 뒤 사용하는 사이에 다른 실행 주체가 상태를 바꾸면 권한 우회, 중복 처리, 데이터 손상 또는 파일 교체가 발생할 수 있다.

### 우선 확인

- `exists()`·권한 확인 뒤 파일을 다시 여는 코드
- 잔액·재고·상태를 읽고 검사한 뒤 별도 쿼리로 갱신하는 코드
- 전역·클래스 변수, singleton, 캐시를 요청·tenant 사이에 공유하는 코드
- check-then-set, lazy initialization, 임시 파일과 lock 없는 read-modify-write
- worker·region 간 중복 메시지와 webhook 재전송

### 안전한 코딩기법

- 검사와 변경을 하나의 원자적 연산으로 결합한다.
- DB 트랜잭션, unique constraint, conditional update, row lock 또는 optimistic version을 사용한다.
- 파일은 배타적·원자적으로 생성·교체하고 심볼릭 링크 정책을 명시한다.
- 공유 상태에는 범위에 맞는 lock을 사용하되 lock 순서와 timeout을 정의한다.
- 메시지 처리에는 idempotency key, deduplication과 원자적 결과 기록을 적용한다.
- GIL을 thread safety의 근거로 삼지 않는다. free-threaded 빌드와 C 확장 동작을 확인한다.

```python
updated = Account.objects.filter(
    pk=account_id,
    balance__gte=amount,
).update(balance=F("balance") - amount)
if updated != 1:
    raise InsufficientFunds
```

동시 요청, 재시도, worker 종료와 lock 경합을 포함한 테스트를 실행한다.

## 2. 종료되지 않는 반복문·재귀와 자원 고갈 (CWE-400, CWE-674, CWE-770, CWE-835)

공격자가 반복 횟수, 재귀 깊이, 큐 길이, 파싱 크기 또는 재시도를 증폭할 수 있으면 CPU·메모리·연결·디스크가 고갈될 수 있다.

### 안전한 코딩기법

- 입력 바이트·문자 수, 항목 수, 깊이와 결과 크기에 상한을 둔다.
- 네트워크·DB·subprocess·lock에 timeout을 적용한다.
- 재시도 횟수, 전체 시간, backoff와 jitter를 제한하고 영구 오류를 분류한다.
- queue length, 동시 실행 수, worker별 CPU·메모리·디스크 예산을 설정한다.
- 재귀 대신 명시적 stack을 검토하고 방문 집합과 최대 깊이를 둔다.
- partial result와 timeout 후 남은 작업이 계속 실행되지 않는지 확인한다.

평균 입력만 측정하지 말고 깊은 JSON·XML, 압축 폭탄, 악성 정규식, 느린 upstream과 큰 결과 집합을 테스트한다.

## 3. 비동기·취소·재시도 상태

`asyncio` 취소, task timeout과 worker 재시작 중 일부 변경만 반영되면 권한·결제·재고 상태가 불일치할 수 있다.

### 안전한 코딩기법

- async 함수 안의 blocking I/O와 CPU 작업을 event loop에서 분리한다.
- 취소 가능한 지점과 반드시 완료해야 하는 cleanup·commit 경계를 구분한다.
- lock, semaphore, connection과 임시 파일을 `async with` 또는 `try/finally`로 정리한다.
- 외부 호출과 DB 변경 순서를 transaction 또는 outbox/saga 패턴으로 조정한다.
- 재시도 가능한 동작을 idempotent하게 만들고 동일 요청의 중복 결과를 막는다.
- task를 생성만 하고 참조·오류 수집·shutdown을 생략하지 않는다.

## 검증 체크리스트

- [ ] 같은 자원에 동시 요청을 보내 invariant가 유지되는지 확인한다.
- [ ] lock timeout, deadlock, cancellation과 worker 강제 종료를 테스트한다.
- [ ] DB 제약과 애플리케이션 검사가 함께 작동하는지 확인한다.
- [ ] retry·redelivery·중복 webhook이 한 번만 효과를 내는지 확인한다.
- [ ] 최대 입력과 느린 dependency에서 자원 예산이 지켜지는지 측정한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [Python asyncio synchronization primitives](https://docs.python.org/3.14/library/asyncio-sync.html)
- [Python asyncio task cancellation](https://docs.python.org/3.14/library/asyncio-task.html#task-cancellation)
- [Python free-threaded HOWTO](https://docs.python.org/3.14/howto/free-threading-python.html)
