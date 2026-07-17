# 제7절 API 오용과 공급망 — 2026 재구성

이 파일은 KISA 「Python 시큐어코딩 가이드」(2023)의 제7절을 2026년 7월 기준으로 교체한 정본이다. API 호출뿐 아니라 지원 종료 런타임, 의존성 선택, 패키징, CI/CD, SBOM과 provenance를 포함한다.

## 목차

1. DNS lookup에 의존한 보안결정
2. 취약한 API·런타임·의존성 사용
3. 소비자 측 패키지 설치
4. 생산자 측 빌드·배포
5. SBOM·취약점 대응과 운영

## 1. DNS lookup에 의존한 보안결정 (CWE-350)

도메인명, reverse DNS 또는 최초 DNS 결과만으로 신뢰·권한을 결정하면 DNS 변조, rebinding, 다중 A·AAAA와 검사-사용 경쟁으로 우회될 수 있다.

### 안전한 코딩기법

- DNS 이름을 사용자·서비스 인증이나 인가의 유일한 근거로 사용하지 않는다.
- 서비스 신원은 TLS 인증서, workload identity, 서명된 토큰과 명시적 정책으로 검증한다.
- 네트워크 목적지 제한이 필요하면 이름 검증과 실제 연결 주소를 일치시키고 모든 A·AAAA 결과를 정책에 대조한다.
- redirect와 재조회마다 동일한 정책을 적용한다.
- egress firewall·service mesh·network policy를 함께 사용한다.
- IP 단순 비교도 proxy, NAT, IPv6, 특수 주소와 운영 변경을 모두 해결하지 못함을 고려한다.

SSRF 입력 검증은 `01-input-validation.md`의 URL·주소·redirect 기준을 함께 적용한다.

## 2. 취약한 API·런타임·의존성 사용 (CWE-1104, CWE-1395)

지원 종료 Python·프레임워크·패키지, 보안 옵션을 끈 API와 유지보수되지 않는 의존성은 알려진 취약점과 새 공격 기법에 노출된다.

### 안전한 코딩기법

- 운영 Python, OS 배포판, 프레임워크와 직접·전이 의존성의 실제 버전을 수집한다.
- upstream 지원 상태와 배포판 backport 여부를 구분한다.
- deprecated·unsafe API와 보안 기본값을 끄는 옵션을 코드에서 검색한다.
- 취약점 번호만 보지 말고 사용 기능, 외부 도달성, 권한과 exploitability를 확인한다.
- 업그레이드 불가 시 격리·기능 비활성화·입력 제한 같은 임시 완화와 종료 기한을 둔다.

2026년 7월 기준 버전 상태를 문서에 고정해 장기간 재사용하지 말고 검토 시 Python 공식 지원 현황과 패키지 공지를 다시 확인한다.

## 3. 소비자 측 패키지 설치 (CWE-494, CWE-1104)

미고정 의존성, 신뢰되지 않은 index·VCS·URL, 설치 시 build script 실행과 dependency confusion은 악성 패키지 또는 예기치 않은 버전을 빌드에 포함시킬 수 있다.

### 안전한 코딩기법

- 애플리케이션 배포 의존성을 직접·전이 항목까지 검증 가능한 lock 파일로 고정한다.
- 도구가 지원하면 표준 `pylock.toml`을 고려하고 lock 생성 환경과 marker를 검토한다.
- pip 배포에는 `--require-hashes`를 사용하고 가능한 경우 wheel과 `--only-binary :all:`로 임의 build 실행을 줄인다.
- `--extra-index-url` 사용 시 공개 index의 더 높은 버전이 선택되는 dependency confusion을 검토한다.
- VCS 의존성은 branch·tag가 아닌 commit으로 고정하고 아티팩트 digest를 검증한다.
- 설치·빌드는 비밀과 운영 네트워크가 없는 격리 환경에서 수행한다.
- typo-squatting, namespace ownership, maintainer 변경과 비정상 release를 검토한다.

lock 파일이 있다는 사실만으로 artifact 출처·해시·빌드 재현성이 보장된다고 가정하지 않는다.

## 4. 생산자 측 빌드·배포 (CWE-494, CWE-1395)

과도한 CI 권한, 변경 가능한 action·image, 외부 PR의 secret 접근과 장기 publish token은 소스부터 배포까지의 공급망을 손상시킬 수 있다.

### 안전한 코딩기법

- PyPI 업로드는 가능하면 OIDC 기반 Trusted Publishing을 사용한다.
- publish workflow의 trigger, environment, reviewer와 권한을 최소화한다.
- third-party action·container·tool은 검토된 digest 또는 commit으로 고정한다.
- 외부 기여 코드가 secret을 가진 runner나 publish job에서 실행되지 않게 분리한다.
- 빌드와 테스트를 격리하고 검증한 아티팩트를 다시 빌드하지 않고 환경 간 승격한다.
- source, build, test, deploy artifact의 digest를 연결하고 rollback 가능한 release를 보존한다.
- provenance·attestation의 signer와 policy를 검증한다.

provenance는 출처를 보강하지만 코드가 선의이거나 무취약하다는 보증은 아니다.

## 5. SBOM·취약점 대응과 운영

현재 dependency 목록과 영향 버전을 식별할 수 없거나 취약점 발견 후 대응 절차가 없으면 패치와 완화가 지연된다.

### 안전한 코딩기법

- release마다 직접·전이 dependency, 버전, 해시, 관계와 생성 시점을 포함한 SBOM을 만든다.
- SBOM을 배포 아티팩트·환경과 연결하고 접근·무결성·보존 정책을 둔다.
- SCA를 PR·CI뿐 아니라 새 advisory를 위한 정기 운영에도 적용한다.
- CVSS만으로 우선순위를 정하지 말고 노출 경로, 사용 기능, 권한, exploit 성숙도와 수정 가능성을 함께 평가한다.
- 취약 package의 수정, 완화, risk acceptance와 종료 기한을 추적한다.
- 비밀 회전, 긴급 release, rollback, 고객 통지와 취약점 접수 절차를 연습한다.
- build·배포·registry 감사 로그와 이상 행위를 모니터링한다.

## 검증 체크리스트

- [ ] 현재 운영 런타임과 직접·전이 의존성의 지원 상태를 확인한다.
- [ ] clean environment에서 lock과 hash만으로 동일 dependency가 설치되는지 확인한다.
- [ ] index, VCS, URL dependency와 build isolation을 검토한다.
- [ ] 외부 PR·fork가 secret, trusted runner와 publish 권한에 접근하지 못하는지 확인한다.
- [ ] action·image·tool pinning과 CI 최소 권한을 확인한다.
- [ ] release SBOM으로 특정 취약 버전의 배포 환경을 찾을 수 있는지 확인한다.
- [ ] 검증 실패 시 publish·deploy가 중단되고 이전 아티팩트로 rollback 가능한지 확인한다.

## 공식 근거

- [KISA Python 시큐어코딩 가이드(2023 개정본)](https://www.kisa.or.kr/2060204/form?board_type=R&lang_type=KO&page=1&postSeq=13&skey=&sval=)
- [KISA SW 공급망 보안 가이드라인 1.0](https://www.kisa.or.kr/2060204/form?page=1&postSeq=15)
- [KISA SW 공급망 보안 강화 로드맵(2026.06.)](https://www.kisa.or.kr/2060204/form?page=1&postSeq=24)
- [Python 지원 버전 현황](https://devguide.python.org/versions/)
- [pip Secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/)
- [PEP 751: pylock.toml](https://peps.python.org/pep-0751/)
- [PyPA Trusted Publishing 권고](https://packaging.python.org/en/latest/guides/tool-recommendations/#uploading-to-pypi)
- [PyPI attestations security model](https://docs.pypi.org/attestations/security-model/)
- [OWASP A03:2025 Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)
- [NIST SP 800-218 SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
