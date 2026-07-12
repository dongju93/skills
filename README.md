# dongju93 Agent Skills

Codex를 비롯한 Agent Skills 호환 에이전트에서 사용할 수 있는 스킬 모음입니다. 각 스킬은 [Agent Skills](https://agentskills.io/) 형식에 따라 독립된 폴더와 `SKILL.md`로 구성됩니다.

## Available skills

| Skill                                                        | Description                                                                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| [`pg-performance-analyzer`](skills/pg-performance-analyzer/) | PostgreSQL 15–18의 실행 계획, 쿼리 병목, 인덱스 전략, AIO 설정을 분석하고 최적화합니다.                      |
| [`python-secure-coding`](skills/python-secure-coding/)       | KISA 「Python 시큐어코딩 가이드」(2023)를 기준으로 Python 코드의 보안 취약점을 검토하고 수정안을 제시합니다. |

## Installation

저장소의 스킬 목록을 확인합니다.

```bash
npx skills add dongju93/dongju93-skills --list
```

대화형으로 설치할 스킬과 대상 에이전트를 선택합니다.

```bash
npx skills add dongju93/dongju93-skills
```

Codex에 특정 스킬을 전역 설치합니다.

```bash
npx skills add dongju93/dongju93-skills --skill pg-performance-analyzer -g -a codex
npx skills add dongju93/dongju93-skills --skill python-secure-coding -g -a codex
```

## Usage

설치 후 에이전트에 작업을 요청하면 관련 스킬이 자동으로 선택됩니다. 이름을 지정해 명시적으로 호출할 수도 있습니다.

```text
Use $pg-performance-analyzer to analyze this EXPLAIN ANALYZE output.
Use $python-secure-coding to review this Django view for security weaknesses.
```

## Repository structure

```text
skills/
├── pg-performance-analyzer/
│   ├── SKILL.md
│   ├── agents/
│   ├── references/
│   └── scripts/
└── python-secure-coding/
    ├── SKILL.md
    ├── agents/
    └── references/
```

각 스킬의 세부 동작, 참고 자료, 스크립트 요구 사항은 해당 폴더의 `SKILL.md`를 확인하세요.
