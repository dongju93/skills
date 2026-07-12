---
name: python-secure-coding
description: >-
  Review Python code for security weaknesses using the KISA "Python 시큐어코딩
  가이드 (2023)". Use this skill WHENEVER reviewing, auditing, or writing Python
  code that touches untrusted input, databases, the filesystem, subprocess/OS
  commands, web frameworks (Django, Flask), XML/LDAP, serialization,
  cryptography, authentication, sessions, cookies, or third-party packages —
  even if the user does not say the words "security" or "시큐어코딩". Trigger on
  requests like "이 코드 보안 점검해줘", "review my Django view", "is this SQL
  safe?", "check for vulnerabilities", "이 함수 취약점 있어?", or any code review
  where injection, path traversal, XSS, weak crypto, hardcoded secrets, or
  unsafe deserialization could be present. Maps each finding to a CWE and the
  guide's safe-coding technique with a fix.
---

# Python 시큐어코딩 리뷰 (KISA 2023)

이 스킬은 KISA 「Python 시큐어코딩 가이드」(2023)를 코드 리뷰·보안 점검에 활용하기 위한 참고 자료다.
7개 절, 43개 보안약점을 다루며 각 약점은 **개요 → 안전한 코딩기법 → 취약/안전 코드 예제 → CWE 참고자료** 순으로 정리되어 있다.

전체 원문은 `references/` 아래 절별 파일에 있다. SKILL.md 본문에는 **빠른 스캔용 위험 패턴 표**와 **전체 약점 인덱스**만 담았다. 특정 약점의 안전한 코딩기법·코드 예제가 필요하면 해당 절 참조파일을 읽어라.

## 리뷰 워크플로우

1. **스코프 파악** — 리뷰 대상 코드가 다루는 것을 확인한다: 외부 입력(request, 파일, 소켓, 환경변수), DB 접근, subprocess/OS 명령, 웹 프레임워크 렌더링, XML/LDAP, 직렬화, 암호화/인증, 세션/쿠키, 서드파티 패키지.
2. **빠른 스캔** — 아래 "위험 패턴 빠른 스캔" 표로 위험 함수·호출을 grep 하듯 훑는다. 매칭되는 패턴이 있으면 해당 약점 번호로 이동한다.
3. **정밀 확인** — 해당 절 참조파일(`references/0N-*.md`)을 읽어 안전한 코딩기법과 취약/안전 예제를 대조한다. 외부 입력이 검증·인자화·이스케이프·화이트리스트 없이 위험 지점에 도달하는 경로(taint flow)가 있는지 판단한다.
4. **보고** — 아래 "발견 항목 보고 형식"에 따라 각 취약점을 보고하고, 가이드의 안전한 코드 예제에 기반한 구체적 수정안을 제시한다.

핵심 원칙: 프레임워크(Django ORM/템플릿, Flask/Jinja2)는 기본적으로 인자화·자동 이스케이프로 보호되지만, `raw()`·`mark_safe`·`autoescape off`·`|safe`·`shell=True`·`eval`/`exec` 등 **보호를 우회하는 지점**에서 취약점이 발생한다. 리뷰 시 이런 우회 지점을 우선 추적한다.

## 위험 패턴 빠른 스캔

코드에서 아래 패턴을 발견하면 대응 약점을 의심하고 해당 절 참조파일을 확인한다.

| 위험 패턴 / 호출 | 의심 약점 | CWE | 참조 |
|---|---|---|---|
| 문자열 결합으로 만든 SQL, `cursor.execute(f"...")`, `Model.objects.raw(query)` | SQL 삽입 | 89 | 01 |
| `eval(`, `exec(`, `compile(` 에 외부 입력 | 코드 삽입 | 94/95 | 01 |
| `open(user_input)`, `os.path` 조합, `socket.bind(port)` | 경로 조작·자원 삽입 | 22/99 | 01 |
| `mark_safe`, `{% autoescape off %}`, `\| safe`, 미이스케이프 렌더링 | XSS | 79 | 01 |
| `os.system`, `subprocess.run(..., shell=True)`, 문자열 명령 | OS 명령어 삽입 | 78 | 01 |
| `FileSystemStorage.save` 검증 없이, 확장자/타입/크기 미검사 | 위험한 파일 업로드 | 434 | 01 |
| `redirect(user_input)`, 외부 URL 리다이렉트 | 오픈 리다이렉트 | 601 | 01 |
| `feature_external_ges=True`, `lxml` `resolve_entities` 기본값, DTD 허용 | XXE | 611 | 01 |
| XPath 문자열 결합, `lxml.etree.XPath` 외부 입력 | XML 삽입 | 643 | 01 |
| `ldap.search` 필터 문자열 결합 | LDAP 삽입 | 90 | 01 |
| `@csrf_exempt`, CSRF 토큰 미적용 폼 | CSRF | 352 | 01 |
| `requests.get(user_url)`, 서버측 외부 요청 | SSRF | 918 | 01 |
| 응답 헤더/쿠키에 개행(`\r\n`) 포함 외부 입력 | HTTP 응답분할 | 113 | 01 |
| 검증 없는 산술로 크기·인덱스·오프셋 계산 | 정수 오버플로우 | 190 | 01 |
| 외부 입력을 보안 결정(권한/인증 분기)에 사용 | 부적절한 보안결정 입력 | 807 | 01 |
| `%`/`.format`/f-string 포맷 문자열에 외부 입력 | 포맷 스트링 삽입 | 134 | 01 |
| 인증 검사 없는 민감 엔드포인트 | 인증 없는 기능 허용 | 306 | 02 |
| 권한 확인 없는 접근, 수평/수직 권한 상승 | 부적절한 인가 | 285 | 02 |
| `os.chmod(0o777)`, 과도한 파일 권한 | 잘못된 권한 설정 | 732 | 02 |
| `DES`, `RC4`, `MD5`/`SHA1`(암호화 용도), ECB 모드 | 취약 암호 알고리즘 | 327 | 02 |
| 평문 저장/전송(민감정보), HTTP 전송 | 미암호화 중요정보 | 312/319 | 02 |
| 소스에 박힌 비밀번호/API키/토큰 | 하드코드된 비밀 | 259/798 | 02 |
| RSA 키 < 2048, 짧은 대칭키 | 불충분한 키 길이 | 326 | 02 |
| `random`(비암호), 예측 가능 시드 | 부적절한 난수 | 330 | 02 |
| 길이·복잡도 미검증 패스워드 허용 | 취약 패스워드 | 521 | 02 |
| 전자서명·인증서 검증 생략(`verify=False`) | 서명/인증서 검증 부재 | 347/295 | 02 |
| 영속 쿠키에 민감정보 저장 | 쿠키 정보 노출 | 539 | 02 |
| 주석에 남은 자격증명·경로·내부정보 | 주석 내 주요정보 | 615 | 02 |
| 솔트 없는 `hashlib` 해시로 비밀번호 저장 | 무솔트 해시 | 759 | 02 |
| 무결성 검사 없는 코드/업데이트 다운로드 | 무결성 미검사 다운로드 | 494 | 02 |
| 로그인 시도 횟수 제한·잠금 부재 | 인증시도 제한 부재 | 307 | 02 |
| 검사 후 사용 사이 상태 변경(파일 등) | TOCTOU 경쟁조건 | 367 | 03 |
| 종료 조건 불명확한 반복/재귀, 외부 입력 기반 | 무한 루프/재귀 | 674 | 03 |
| 예외 메시지·스택트레이스 사용자 노출, `DEBUG=True` | 오류 메시지 정보노출 | 209 | 04 |
| 예외를 무시(`except: pass`)·미처리 | 오류상황 대응 부재 | 390 | 04 |
| 광범위 `except Exception`, 부적절 예외 처리 | 부적절한 예외 처리 | 754 | 04 |
| None 반환값 미확인 후 역참조 | Null 역참조 | 476 | 05 |
| 파일/소켓/락 미해제, `with` 미사용 | 부적절한 자원 해제 | 404 | 05 |
| `pickle.loads`, `yaml.load`, 신뢰불가 역직렬화 | 안전하지 않은 역직렬화 | 502 | 05 |
| 세션 혼동·공유로 타 사용자 데이터 노출 | 세션 데이터 노출 | 488 | 06 |
| 남은 디버그 코드·백도어·`pdb` | 디버그 코드 잔존 | 489 | 06 |
| private 배열 참조를 그대로 반환 | Private 배열 반환 | 495 | 06 |
| public 데이터를 private 배열에 직접 할당 | Private 배열 할당 | 496 | 06 |
| DNS 조회 결과로 보안 결정 | DNS 의존 보안결정 | 350 | 07 |
| 취약/미유지보수 패키지, SBOM 부재 | 취약한 API 사용 | — | 07 |

## 전체 약점 인덱스

각 약점의 상세(개요·안전한 코딩기법·코드 예제·참고자료)는 표시된 참조파일에서 확인한다.

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
6. 하드코드된 중요정보 (CWE-259)
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
2. 종료되지 않는 반복문 또는 재귀 함수 (CWE-674)

### 제4절 에러처리 — `references/04-error-handling.md`
1. 오류 메시지 정보노출 (CWE-209)
2. 오류상황 대응 부재 (CWE-390)
3. 부적절한 예외 처리 (CWE-754)

### 제5절 코드오류 — `references/05-code-errors.md`
1. Null Pointer 역참조 (CWE-476)
2. 부적절한 자원 해제 (CWE-404)
3. 신뢰할 수 없는 데이터의 역직렬화 (CWE-502)

### 제6절 캡슐화 — `references/06-encapsulation.md`
1. 잘못된 세션에 의한 데이터 정보 노출 (CWE-488)
2. 제거되지 않고 남은 디버그 코드 (CWE-489)
3. Public 메소드로부터 반환된 Private 배열 (CWE-495)
4. Private 배열에 Public 데이터 할당 (CWE-496)

### 제7절 API 오용 — `references/07-api-abuse.md`
1. DNS lookup에 의존한 보안결정 (CWE-350)
2. 취약한 API 사용 (SBOM/취약 패키지 관리)

## 발견 항목 보고 형식

리뷰 결과는 심각도 순으로 정렬해 각 항목마다 아래 구조로 보고한다. 코드가 안전하면 그 근거(예: 인자화된 쿼리 사용, 자동 이스케이프 적용)를 간단히 밝힌다.

```
### [심각도] 약점명 (CWE-NNN)
- 위치: 파일:라인 (또는 함수명)
- 문제: 어떤 외부 입력이 어떤 위험 지점에 검증 없이 도달하는지, 악용 시나리오
- 근거: 가이드의 안전한 코딩기법 요약
- 수정안: 가이드 안전 예제에 기반한 구체적 코드 (인자화/이스케이프/화이트리스트 등)
```

심각도는 악용 가능성과 영향(코드/명령 실행 > 정보 노출 > 서비스 장애)을 기준으로 High/Medium/Low로 판단한다.

## 유의사항

- 이 가이드는 Django/Flask 기준 예제가 많다. FastAPI·기타 프레임워크에도 동일 원칙(인자화·이스케이프·화이트리스트·최소권한)을 적용해 판단한다.
- 원문 예제 코드는 들여쓰기·오타가 일부 있으니 로직과 기법 위주로 해석한다.
- CWE 번호는 MITRE(cwe.mitre.org/data/definitions/NNN.html), OWASP Cheat Sheet와 교차 확인하면 근거가 강화된다.
