---
name: python-secure-coding
description: >-
  Review and write Python code using a 2026 secure-coding baseline reconstructed
  from KISA's 2023 Python guide, KISA's 2024-2026 software supply-chain
  guidance, current Python documentation, OWASP Top 10:2025, and modern PyPA
  practices. Use this skill whenever Python code touches untrusted input,
  authentication or authorization, databases, templates, files or archives,
  subprocesses, outbound network requests, XML or serialization, cryptography,
  sessions or tokens, async/concurrent execution, AI or agent tools, CI/CD,
  package installation, or third-party dependencies. Trigger on security
  reviews and ordinary Python reviews where injection, traversal, SSRF, XSS,
  unsafe deserialization, resource exhaustion, broken access control, secret
  exposure, insecure dependencies, or build-pipeline compromise could exist.
  Trace exploitable data flow, map findings to CWE when appropriate, and give a
  concrete fix and verification method.
---

## 참조파일 선택

대상 코드와 관련된 절별 파일만 읽는다. 선택한 파일에 판정·수정·검증 근거가 있으면 다른 절을 보강용으로 읽지 않는다. 서로 독립적인 추가 약점이 실제로 드러나고 선택한 파일만으로 판정할 수 없을 때만 해당 절을 추가로 읽는다.

- 입력·DB·파일·명령·템플릿·XML·외부 URL: `references/01-input-validation.md`
- 인증·인가·암호화·비밀·서명·TLS·쿠키: `references/02-security-features.md`
- 경쟁조건·비동기·종료 조건·자원 예산: `references/03-time-and-state.md`
- 오류 응답·fail-open·예외·보안 로깅: `references/04-error-handling.md`
- None·자원 수명주기·역직렬화: `references/05-code-errors.md`
- 세션 격리·디버그 코드·가변 객체 캡슐화: `references/06-encapsulation.md`
- DNS 보안결정·런타임·의존성·빌드 공급망: `references/07-api-abuse.md`

Python·프레임워크·패키지 버전에 따라 동작이 달라지면 현재 공식 문서를 확인한다. 버전 번호만으로 안전성을 추정하지 않는다.

## 리뷰 워크플로우

1. **스코프와 신뢰 경계 식별** — HTTP·WebSocket·CLI·파일·큐·DB·환경변수·모델 출력·외부 API 응답 등 입력 출처와 인증 주체를 나눈다.
2. **보호 자산과 위험 동작 식별** — 데이터 변경, 권한 결정, 파일·프로세스·네트워크 접근, 템플릿 렌더링, 역직렬화, 암호화, 패키지 설치·빌드를 표시한다.
3. **소스-싱크 데이터 흐름 추적** — 공격자 통제 값이 검증·정규화·인자화·출력 인코딩·권한 확인 없이 위험 동작에 도달하는지 확인한다. 위험 함수 이름만으로 취약점을 단정하지 않는다.
4. **인가와 소유권 확인** — 인증 여부뿐 아니라 요청 주체가 해당 객체·필드·행위를 수행할 권한이 있는지 모든 실행 경로에서 확인한다.
5. **자원 예산 확인** — 입력 크기, 압축 해제 크기, 중첩 깊이, 반복 횟수, 시간 제한, 동시성, 메모리·디스크 사용량을 공격자가 증폭할 수 있는지 확인한다.
6. **공급망과 런타임 확인** — 지원 중인 Python, 고정·해시된 의존성, 잠금 파일, 패키지 출처, 취약점 점검, SBOM, 빌드·배포 권한과 provenance를 확인한다.
7. **증거 중심으로 보고** — 실제 데이터 흐름, 악용 전제, 영향, 기존 방어, 수정안, 검증 방법을 함께 제시한다. 도달 가능성이나 환경을 확인하지 못하면 불확실성을 명시한다.

핵심 원칙은 **프레임워크의 안전한 기본값을 유지하고 우회 지점을 추적하는 것**이다. Django ORM·Jinja 자동 이스케이프·TLS 인증서 검증 같은 기본 보호가 있어도 `raw()`·`mark_safe`·`|safe`·`shell=True`·`verify=False`·`eval`·동적 템플릿·임의 URL 요청·임의 패키지 설치처럼 보호를 끄거나 경계를 넓히는 코드에서 취약점이 발생한다.

## 2026 우선 스캔

아래 패턴은 후보를 찾기 위한 출발점이다. 매칭만으로 취약점을 확정하지 말고 입력의 통제 가능성, 도달 경로, 실행 환경과 기존 방어를 확인한다.

| 위험 패턴 / 호출                                            | 우선 확인할 문제               | CWE 예시      | 상세   |
| ----------------------------------------------------------- | ------------------------------ | ------------- | ------ |
| `eval`, `exec`, 외부 입력을 `compile`                       | 코드 삽입                      | 94/95         | 01     |
| 문자열 SQL, `raw()`·`text()`에 결합된 입력                  | SQL 삽입                       | 89            | 01     |
| `shell=True`, `os.system`, 문자열 명령                      | OS 명령어 삽입                 | 78            | 01     |
| 사용자 경로를 `open`·삭제·압축 해제에 사용                  | 경로 순회·임의 파일 접근       | 22/23         | 01     |
| `extractall`, ZIP/TAR, 압축·이미지·문서 처리                | Zip Slip·압축 폭탄·자원 고갈   | 22/409/400    | 01     |
| 사용자 문자열을 템플릿 소스로 컴파일                        | 서버사이드 템플릿 삽입         | 1336          | 01     |
| `mark_safe`, `\|safe`, `autoescape off`                     | XSS                            | 79            | 01     |
| 업로드 이름·확장자만 신뢰하거나 웹 루트에 저장              | 위험한 파일 업로드             | 434           | 01     |
| `requests.get(user_url)`, webhook·미리보기·가져오기         | SSRF·DNS rebinding             | 918           | 01     |
| 외부 URL로 `redirect`                                       | 오픈 리다이렉트                | 601           | 01     |
| 외부 입력을 응답 헤더나 로그에 직접 기록                    | 응답 분할·로그 위조            | 113/117       | 01, 04 |
| 외부 XML, 오래된 Expat, DTD·외부 엔티티 허용                | XXE·XML DoS                    | 611/776/400   | 01     |
| `pickle`, `shelve`, `marshal`, `yaml.load`에 비신뢰 데이터  | 안전하지 않은 역직렬화         | 502           | 05     |
| 사용자 정규식·중첩 수량자·무제한 매칭                       | ReDoS·과도한 계산              | 1333/400      | 01     |
| 요청·파싱·subprocess에 timeout·크기 제한 없음               | 자원 고갈                      | 400/770       | 03, 05 |
| ID만으로 객체 조회·수정, 소유권 확인 없음                   | 객체 수준 인가 실패            | 285/639       | 02     |
| 요청 dict를 모델·ORM에 통째로 적용                          | 대량 할당·보호 필드 변경       | 915           | 01     |
| JWT 검증 알고리즘을 토큰에서 선택, `verify_signature=False` | 서명 검증·인증 우회            | 347/287       | 02     |
| `verify=False`, 호스트명 확인 해제, 평문 프로토콜           | 인증서 검증·평문 전송 실패     | 295/319       | 02     |
| AES-ECB/CBC만 사용, 고정 IV, 직접 만든 암호화               | 암호 실패·무결성 부재          | 327/329       | 02     |
| SHA-256·MD5 같은 빠른 해시로 비밀번호 저장                  | 부적절한 비밀번호 저장         | 916/759       | 02     |
| `random`으로 토큰·OTP·키 생성                               | 예측 가능한 난수               | 330           | 02     |
| 코드·설정·테스트·로그에 비밀 포함                           | 하드코드·비밀 노출             | 798/532       | 02, 04 |
| 쿠키에 `Secure`·`HttpOnly`·`SameSite` 누락                  | 세션·쿠키 노출                 | 614/1004/1275 | 02     |
| `DEBUG=True`, 대화형 디버거, 상세 traceback 응답            | 정보 노출·디버그 코드          | 209/489       | 04, 06 |
| `except: pass`, 보안 오류 후 기본 허용                      | 예외 처리 실패·fail-open       | 390/754       | 04     |
| 전역·클래스 가변 상태를 요청 간 공유                        | 세션 데이터 노출·경쟁조건      | 488/362       | 03, 06 |
| 미고정 의존성, `--extra-index-url`, 해시 없는 자동 설치     | 의존성 혼동·공급망 실패        | 1104/1395/494 | 07     |
| 지원 종료 Python·프레임워크·패키지                          | 알려진 취약점·패치 부재        | 1104/1395     | 07     |
| 모델 출력이 파일·SQL·명령·도구 인자로 직결                  | 프롬프트 삽입의 권한 경계 우회 | 94/78/918/285 | 01     |

## 약점 인덱스

### 제1절 입력데이터 검증 및 표현 — `references/01-input-validation.md`

1. SQL 삽입 (CWE-89)
2. 코드 삽입 (CWE-94, 95)
3. 경로 조작 및 자원 삽입 (CWE-22, 99)
4. 크로스사이트 스크립트(XSS) (CWE-79)
5. 운영체제 명령어 삽입 (CWE-78)
6. 위험한 형식 파일 업로드 (CWE-434)
7. 신뢰되지 않은 URL주소로 자동접속 연결 (CWE-601)
8. 부적절한 XML 외부 개체 참조 (CWE-611)
9. XML 삽입 (CWE-643)
10. LDAP 삽입 (CWE-90)
11. 크로스사이트 요청 위조(CSRF) (CWE-352)
12. 서버사이드 요청 위조 (CWE-918)
13. HTTP 응답분할 (CWE-113)
14. 정수형 오버플로우 (CWE-190)
15. 보안기능 결정에 사용되는 부적절한 입력값 (CWE-807)
16. 포맷 스트링 삽입 (CWE-134)

### 제2절 보안기능 — `references/02-security-features.md`

1. 적절한 인증 없는 중요 기능 허용 (CWE-306)
2. 부적절한 인가 (CWE-285)
3. 중요한 자원에 대한 잘못된 권한 설정 (CWE-732)
4. 취약한 암호화 알고리즘 사용 (CWE-327)
5. 암호화되지 않은 중요정보 (CWE-312, 319)
6. 하드코드된 중요정보 (CWE-259, 321, 798)
7. 충분하지 않은 키 길이 사용 (CWE-326)
8. 적절하지 않은 난수 값 사용 (CWE-330)
9. 취약한 패스워드 허용 (CWE-521)
10. 부적절한 전자서명 확인 (CWE-347)
11. 부적절한 인증서 유효성 검증 (CWE-295)
12. 사용자 하드디스크에 저장되는 쿠키를 통한 정보 노출 (CWE-539)
13. 주석문 안에 포함된 시스템 주요정보 (CWE-615)
14. 솔트 없이 일방향 해시 함수 사용 (CWE-759)
15. 무결성 검사없는 코드 다운로드 (CWE-494)
16. 반복된 인증시도 제한 기능 부재 (CWE-307)

### 제3절 시간 및 상태 — `references/03-time-and-state.md`

1. 경쟁조건: 검사시점과 사용시점(TOCTOU) (CWE-367)
2. 종료되지 않는 반복문 또는 재귀 함수 (CWE-674, 835)

### 제4절 에러처리 — `references/04-error-handling.md`

1. 오류 메시지 정보노출 (CWE-209)
2. 오류상황 대응 부재 (CWE-390)
3. 부적절한 예외 처리 (CWE-754)

### 제5절 코드오류 — `references/05-code-errors.md`

1. None 역참조 (CWE-476)
2. 부적절한 자원 해제 (CWE-404)
3. 신뢰할 수 없는 데이터의 역직렬화 (CWE-502)

### 제6절 캡슐화 — `references/06-encapsulation.md`

1. 잘못된 세션에 의한 데이터 정보 노출 (CWE-488)
2. 제거되지 않고 남은 디버그 코드 (CWE-489)
3. Public 메소드로부터 반환된 Private 가변 객체 (CWE-495)
4. Private 가변 객체에 Public 데이터 할당 (CWE-496)

### 제7절 API 오용 — `references/07-api-abuse.md`

1. DNS lookup에 의존한 보안결정 (CWE-350)
2. 취약한 API·런타임·의존성 및 공급망 관리 (CWE-1104, 1395 등)

## 발견 항목 보고 형식

실제 취약점만 심각도 순으로 먼저 보고한다. 일반적인 개선 제안은 취약점과 분리한다. 코드가 안전하면 어떤 방어가 어떤 공격 경로를 차단하는지 간단히 밝힌다.

```text
### [High|Medium|Low] 약점명 (CWE-NNN)
- 위치: 파일:라인 또는 함수명
- 신뢰 경계: 공격자가 통제하는 입력과 권한
- 데이터 흐름: source -> 변환/검증 -> sink
- 영향과 악용 전제: 가능한 결과, 필요한 조건, 기존 완화책
- 근거: 2026 기준과 적용 이유
- 수정안: 최소한의 구체적 코드 또는 설계 변경
- 검증: 회귀 테스트, 악성 입력, 설정 또는 배포 확인 방법
- 확신도: High|Medium|Low와 미확인 사항
```

심각도는 코드·명령 실행, 인증·인가 우회, 민감정보 노출, 무결성 훼손, 서비스 거부의 실제 영향과 외부 도달성·권한·복잡도를 함께 고려한다. 위험 함수가 있다는 이유만으로 High를 부여하지 않는다.

## 리뷰 유의사항

- CWE는 분류 수단이지 취약성의 증명이 아니다. 가장 구체적인 원인 CWE를 우선하고 중복 매핑을 남발하지 않는다.
- `안전한 라이브러리 사용`만 제안하지 말고 필요한 옵션, 경계 검사, 실패 동작, 운영 통제를 제시한다.
- 비밀을 환경변수로 옮기는 것은 소스 하드코딩을 줄일 뿐 완전한 비밀 관리가 아니다. 접근 제어·회전·감사 가능한 비밀 저장소를 우선한다.
- 해시·서명은 출처와 무결성의 일부만 보장한다. 서명된 코드나 패키지도 악성일 수 있으므로 신뢰 정책과 빌드 provenance를 함께 확인한다.
- 네트워크·파일·subprocess·DB·락은 timeout과 수명주기를 확인하고 컨텍스트 관리자나 명시적 정리 절차를 사용한다.
- 테스트가 통과해도 동시성, 운영 설정, 배포 권한, 프록시·스토리지 동작이 달라질 수 있다. 확인한 범위를 결과에 명시한다.
