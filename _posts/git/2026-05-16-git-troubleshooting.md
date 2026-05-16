---
title: "Git 트러블슈팅 완벽 가이드 — 충돌 해결부터 사고 복구까지"
categories: GIT
tags: [Git, 충돌해결, GitLFS, SparseCheckout, 사고복구, 대용량리포, filter-branch]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-16
---

실무에서 Git을 쓰다 보면 Merge 충돌, 대용량 리포 클론 30분, 비밀키 유출, force push 사고 같은 문제를 반드시 만나게 된다. 이 글에서는 **10GB 리포, 10만 커밋 히스토리, 모노레포 성능 저하, 비밀키 유출 대응** 같은 극한 시나리오를 포함해 현장에서 자주 발생하는 Git 트러블을 원인-진단-해결-예방 순서로 정리한다.

> **비유로 먼저 이해하기**: Git 리포지토리는 거대한 도서관이다. 커밋은 도서 카탈로그 카드, 브랜치는 카탈로그 분류 라벨, `.git` 폴더는 서고 자체다. 충돌은 두 사서가 같은 카드를 동시에 고쳐 쓴 상황이고, force push는 카탈로그 서랍을 통째로 바꿔치기한 것이다. 이 비유를 기억하면 트러블슈팅의 큰 그림이 잡힌다.

---

## 한 줄 요약

Git 사고의 80%는 **3-way merge 이해 부족, .gitignore 미설정, force push 오남용**에서 비롯되며, 나머지 20%는 대용량 리포 관리와 민감 정보 유출이다. 이 글 하나로 전부 해결할 수 있다.

---

## 1. 충돌 해결 전략

### 1-1. 3-way Merge 원리

Git의 merge는 단순히 두 파일을 비교하는 것이 아니다. **공통 조상(base)**, **현재 브랜치(ours)**, **대상 브랜치(theirs)** 세 버전을 동시에 비교하는 3-way merge 알고리즘을 사용한다.

> **비유**: 두 명의 번역가가 같은 원서(base)를 각자 번역했다. 편집자(Git)는 원서와 두 번역본을 나란히 놓고, 원서와 같은 부분은 변경된 쪽을 채택하고, 둘 다 다르게 고친 부분만 "충돌"로 표시한다. 원서 없이 두 번역본만 비교하면(2-way) 어디가 원래 내용인지 알 수 없어 충돌이 훨씬 많아진다.

```mermaid
graph LR
    BASE["Base: 공통 조상"] --> OURS["Ours: 내 브랜치"]
    BASE --> THEIRS["Theirs: 대상 브랜치"]
    OURS --> MERGE["3-way Merge"]
    THEIRS --> MERGE
    MERGE --> RESULT["병합 결과"]
```

3-way merge 판정 규칙은 다음과 같다.

| Base | Ours | Theirs | 결과 |
|------|------|--------|------|
| A | A | B | B (theirs 변경 채택) |
| A | B | A | B (ours 변경 채택) |
| A | B | B | B (양쪽 동일 변경) |
| A | B | C | **충돌** (양쪽 다른 변경) |
| A | A | A | A (변경 없음) |

### 1-2. 충돌 해결 도구별 가이드

#### IntelliJ IDEA

IntelliJ는 3-way merge 에디터를 내장하고 있어 가장 직관적이다.

**해결 단계:**

1. `Git > Merge` 또는 `Git > Rebase` 수행
2. 충돌 발생 시 **Merge Conflicts** 다이얼로그 자동 표시
3. 파일 선택 후 **Merge** 클릭 — 3-패널 에디터 열림
4. 좌측(Ours) / 우측(Theirs) / 중앙(Result) 패널에서 화살표 클릭으로 변경 채택
5. 수동 편집이 필요하면 중앙 패널에서 직접 수정
6. **Apply** 클릭 후 커밋

```
// IntelliJ 3-way merge 에디터 레이아웃
┌──────────────┬──────────────┬──────────────┐
│   Ours       │   Result     │   Theirs     │
│  (내 변경)    │  (최종 결과)  │  (상대 변경)  │
│              │              │              │
│  >>  Accept  │  직접 편집    │  Accept  <<  │
└──────────────┴──────────────┴──────────────┘
```

#### VS Code

1. 충돌 파일 열기 — 충돌 마커 위에 **Accept Current / Accept Incoming / Accept Both** 버튼 표시
2. 복잡한 충돌은 **GitLens** 확장을 설치하면 3-way diff 뷰 사용 가능
3. `Ctrl+Shift+P > Merge Editor` 로 3-패널 뷰 전환

```bash
# VS Code에서 merge tool로 설정
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'
```

#### kdiff3 (CLI 환경)

```bash
# kdiff3 설치 후 설정
git config --global merge.tool kdiff3
git config --global mergetool.kdiff3.path "/usr/bin/kdiff3"

# 충돌 발생 시 실행
git mergetool
```

### 1-3. ours / theirs 전략

때로는 한쪽을 통째로 채택하는 것이 정답일 때가 있다.

```bash
# 파일 단위로 한쪽 채택
git checkout --ours path/to/file.txt      # 내 변경 유지
git checkout --theirs path/to/file.txt    # 상대 변경 채택
git add path/to/file.txt

# 전체 머지를 한쪽으로 강제 (주의: 상대 변경 전부 무시)
git merge -X ours feature-branch
git merge -X theirs feature-branch
```

> **비유**: ours/theirs는 재판에서 "원고 전면 승소" 또는 "피고 전면 승소"를 선언하는 것과 같다. 세밀한 판결(줄 단위 머지)이 불가능할 때만 써야 한다.

**주의 사항:** `rebase` 중에는 ours/theirs의 의미가 뒤바뀐다. rebase는 대상 브랜치 위에 내 커밋을 하나씩 재적용하므로, 현재 적용 중인 커밋이 "theirs"가 되고 대상 브랜치가 "ours"가 된다.

```bash
# rebase 중 충돌 해결 — 의미 주의!
# git rebase main 에서 충돌 시:
#   --ours   = main (rebase 대상)
#   --theirs = 내 커밋 (적용 중인 커밋)
git checkout --theirs path/to/file.txt  # rebase 시 내 변경 유지
```

### 1-4. 충돌 예방 전략

충돌을 줄이는 것이 해결보다 낫다.

```bash
# 1. 자주 리베이스 — 충돌 범위를 작게 유지
git fetch origin
git rebase origin/main

# 2. 충돌 기록 재사용 (rerere)
git config --global rerere.enabled true
# 한번 해결한 충돌 패턴을 기억해 자동 적용

# 3. merge 전 드라이런
git merge --no-commit --no-ff feature-branch
git diff --cached  # 결과 미리 확인
git merge --abort  # 필요 시 취소
```

```mermaid
graph LR
    FETCH["git fetch"] --> REBASE["rebase main"]
    REBASE --> CONFLICT{"충돌?"}
    CONFLICT -->|없음| PUSH["push"]
    CONFLICT -->|있음| RERERE{"rerere 기록?"}
    RERERE -->|있음| AUTO["자동 해결"]
    RERERE -->|없음| MANUAL["수동 해결"]
```

---

## 2. 대용량 리포 관리

### 2-1. Git LFS (Large File Storage)

Git은 텍스트 파일에 최적화되어 있다. 바이너리 파일(이미지, 동영상, ML 모델, 빌드 산출물)이 쌓이면 리포 크기가 기하급수적으로 증가한다.

> **비유**: Git LFS는 도서관의 "대형 도서 별도 보관 시스템"이다. 카탈로그 카드(포인터 파일)에는 "이 책은 별도 서고 B-3-17에 있음"이라고만 적고, 실제 대형 도서(바이너리)는 별도 서고(LFS 서버)에 보관한다. 카탈로그(Git 히스토리)가 가벼워져 검색이 빨라진다.

```mermaid
graph LR
    COMMIT["git commit"] --> PTR["포인터 파일 저장"]
    PTR --> GIT["Git 저장소: 가벼움"]
    COMMIT --> BLOB["원본 바이너리"]
    BLOB --> LFS["LFS 서버: 대용량"]
    CHECKOUT["git checkout"] --> LFS
    LFS --> LOCAL["로컬 파일 복원"]
```

**설정 및 사용:**

```bash
# 1. LFS 설치
git lfs install

# 2. 추적 대상 지정
git lfs track "*.psd"
git lfs track "*.mp4"
git lfs track "models/*.bin"

# 3. .gitattributes 커밋 (반드시 먼저!)
git add .gitattributes
git commit -m "Configure Git LFS tracking"

# 4. 이후 파일 추가는 평소와 동일
git add design/hero.psd
git commit -m "Add hero banner design"

# 5. LFS 상태 확인
git lfs ls-files         # 추적 중인 파일 목록
git lfs status           # 스테이징 상태
git lfs env              # LFS 설정 정보
```

**기존 리포에 LFS 도입 (히스토리 재작성):**

```bash
# 기존 바이너리를 LFS로 마이그레이션 (히스토리 전체 재작성)
git lfs migrate import --include="*.psd,*.mp4" --everything

# 특정 브랜치만
git lfs migrate import --include="*.psd" --include-ref=refs/heads/main

# 마이그레이션 후 용량 확인
git lfs migrate info --everything
```

**극한 시나리오 — 10GB 리포에서 LFS 마이그레이션:**

10GB 리포의 히스토리를 전부 재작성하면 수 시간이 걸릴 수 있다. 이때는 단계적 접근이 필요하다.

```bash
# 1. 어떤 파일이 용량을 차지하는지 분석
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | \
  sort -rnk2 | head -20

# 2. 상위 용량 파일 확장자별 통계
git lfs migrate info --everything --top=10

# 3. 가장 큰 확장자부터 단계적 마이그레이션
git lfs migrate import --include="*.bin" --everything
git lfs migrate import --include="*.mp4" --everything

# 4. 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 2-2. Sparse Checkout

모노레포에서 전체 소스를 체크아웃할 필요가 없을 때 사용한다.

> **비유**: Sparse Checkout은 거대한 백화점에서 특정 매장(디렉토리)만 불을 켜는 것과 같다. 나머지 매장은 존재하지만 어둡게 두어(체크아웃하지 않아) 전력(디스크, 시간)을 아낀다.

```bash
# 1. Sparse Checkout 활성화 (cone 모드 — 빠르고 안정적)
git clone --no-checkout https://github.com/company/monorepo.git
cd monorepo
git sparse-checkout init --cone

# 2. 필요한 디렉토리만 지정
git sparse-checkout set backend/api backend/common shared/proto

# 3. 체크아웃
git checkout main

# 4. 디렉토리 추가/제거
git sparse-checkout add frontend/dashboard
git sparse-checkout list

# 5. Sparse Checkout 해제
git sparse-checkout disable
```

### 2-3. Partial Clone

Sparse Checkout이 "어떤 파일을 체크아웃할까"를 제어한다면, Partial Clone은 "어떤 객체를 다운로드할까"를 제어한다.

```bash
# 블롭 없이 클론 (트리와 커밋만 가져옴)
git clone --filter=blob:none https://github.com/company/monorepo.git

# 특정 크기 이상 블롭 제외
git clone --filter=blob:limit=1m https://github.com/company/monorepo.git

# 트리도 제외 (가장 가벼운 클론)
git clone --filter=tree:0 https://github.com/company/monorepo.git

# Partial Clone + Sparse Checkout 조합 (최적 조합)
git clone --filter=blob:none --sparse https://github.com/company/monorepo.git
cd monorepo
git sparse-checkout set backend/api
```

### 2-4. Shallow Clone

히스토리 깊이를 제한하여 클론 속도를 높인다. CI/CD에서 가장 자주 쓰인다.

```bash
# 최근 1개 커밋만 (CI/CD 빌드용)
git clone --depth 1 https://github.com/company/repo.git

# 최근 10개 커밋
git clone --depth 10 https://github.com/company/repo.git

# 이후 히스토리가 필요하면 점진적으로 가져오기
git fetch --deepen=50
git fetch --unshallow  # 전체 히스토리 복원
```

**각 방법 비교:**

| 기법 | 클론 시간 | 디스크 | 히스토리 | 적합 용도 |
|------|----------|--------|---------|----------|
| 일반 클론 | 느림 | 전체 | 전체 | 소규모 리포 |
| Shallow Clone | 매우 빠름 | 최소 | 제한적 | CI/CD 빌드 |
| Partial Clone | 빠름 | 필요시 다운로드 | 전체 | 대규모 리포 개발 |
| Sparse Checkout | 보통 | 선택적 | 전체 | 모노레포 특정 프로젝트 |
| LFS | 보통 | 포인터만 | 전체 | 바이너리 파일 관리 |

```mermaid
graph LR
    REPO["대용량 리포"] --> Q1{"바이너리 많음?"}
    Q1 -->|예| LFS["Git LFS"]
    Q1 -->|아니오| Q2{"일부만 필요?"}
    Q2 -->|예| SPARSE["Sparse Checkout"]
    Q2 -->|아니오| Q3{"CI/CD용?"}
    Q3 -->|예| SHALLOW["Shallow Clone"]
    Q3 -->|아니오| PARTIAL["Partial Clone"]
```

---

## 3. 민감 정보 유출 복구

### 3-1. 유출 감지

비밀키, DB 비밀번호, API 토큰이 커밋에 포함된 것을 발견했다면, **즉시 대응**해야 한다. 커밋을 지워도 reflog과 원격 캐시에 남아있기 때문이다.

> **비유**: 민감 정보 유출은 아파트 마스터키를 복사해서 전단지에 인쇄한 것과 같다. 전단지(커밋)를 수거하는 것도 중요하지만, 그보다 먼저 **잠금장치를 교체(키 로테이션)**해야 한다. 누가 이미 전단지를 가져갔는지 알 수 없기 때문이다.

**즉시 대응 순서:**

1. **키 로테이션** — 유출된 키/비밀번호를 즉시 폐기하고 새로 발급
2. **영향 범위 파악** — 해당 키로 접근 가능한 시스템 확인
3. **히스토리에서 제거** — BFG 또는 git filter-repo 사용
4. **모니터링** — 이상 접근 로그 확인

### 3-2. BFG Repo-Cleaner

```bash
# 1. bare 클론 생성 (원본 보호)
git clone --mirror https://github.com/company/repo.git
cd repo.git

# 2. 특정 파일 제거
java -jar bfg.jar --delete-files "credentials.json"

# 3. 특정 텍스트 치환
echo "AKIAIOSFODNN7EXAMPLE" >> passwords.txt
java -jar bfg.jar --replace-text passwords.txt

# 4. 특정 크기 이상 파일 제거 (100MB 이상)
java -jar bfg.jar --strip-blobs-bigger-than 100M

# 5. 정리 및 푸시
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

### 3-3. git filter-repo (권장)

`git filter-branch`는 공식적으로 deprecated되었다. `git filter-repo`가 10배 이상 빠르고 안전하다.

```bash
# 설치
pip install git-filter-repo

# 특정 파일을 히스토리 전체에서 제거
git filter-repo --invert-paths --path secrets/config.yaml

# 특정 패턴 텍스트 치환
git filter-repo --replace-text <(echo 'regex:AKIA[A-Z0-9]{16}==>REDACTED')

# 특정 디렉토리만 남기기 (모노레포 분리 시)
git filter-repo --path backend/api/ --path shared/

# 커미터 이메일 변경
git filter-repo --mailmap my-mailmap
```

**극한 시나리오 — 10만 커밋에서 비밀키 제거:**

```bash
# 1. 소요 시간 예측 (10만 커밋 기준 약 5-15분)
git rev-list --count --all  # 커밋 수 확인

# 2. filter-repo 실행 (BFG보다 대규모에서 안정적)
git filter-repo --replace-text expressions.txt --force

# 3. 모든 팀원에게 reclone 안내
# 기존 클론은 히스토리가 달라져 push/pull 불가능
# git clone --fresh 필수

# 4. GitHub에서 캐시 삭제 요청
# Settings > Actions > Caches 에서 수동 삭제
# GitHub Support에 sensitive data removal 요청
```

### 3-4. 사전 예방

```bash
# 1. pre-commit 훅으로 비밀키 패턴 차단
# .pre-commit-config.yaml
# repos:
#   - repo: https://github.com/Yelp/detect-secrets
#     hooks:
#       - id: detect-secrets
#         args: ['--baseline', '.secrets.baseline']

# 2. .gitignore에 민감 파일 등록
echo "*.pem" >> .gitignore
echo ".env" >> .gitignore
echo "credentials.*" >> .gitignore

# 3. git-secrets 설치 (AWS 키 자동 감지)
git secrets --install
git secrets --register-aws
```

---

## 4. Force Push 사고 복구

### 4-1. 사고 발생 시나리오

> **비유**: force push는 도서관 카탈로그 서랍을 통째로 교체하는 것이다. 교체 전 서랍이 어딘가에 사본으로 남아 있다면 복구할 수 있지만, 사본까지 사라지면 영영 복구 불가능하다.

force push로 원격 브랜치의 커밋이 사라지는 가장 흔한 시나리오:

```bash
# 사고 시나리오: 개인 브랜치를 rebase 후 force push하려다
# 실수로 main에 force push
git checkout main
git rebase feature-branch   # 의도하지 않은 rebase
git push --force origin main  # 재앙
```

### 4-2. 복구 방법

**방법 1: 로컬 reflog (본인 PC에 기록이 있을 때)**

```bash
# 1. reflog에서 사고 이전 커밋 찾기
git reflog show origin/main
# 출력 예시:
# abc1234 origin/main@{0}: update by push  (사고 후)
# def5678 origin/main@{1}: update by push  (사고 전 — 이것!)

# 2. 원래 상태로 복구
git push --force origin def5678:refs/heads/main
```

**방법 2: 팀원의 로컬 저장소**

```bash
# 팀원이 force push 이전 상태를 가지고 있을 때
# 팀원 PC에서:
git log origin/main --oneline -10  # 이전 커밋 확인
git push --force origin origin/main:refs/heads/main
```

**방법 3: GitHub 이벤트 로그**

```bash
# GitHub API로 push 이벤트 조회
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/events | \
  jq '.[] | select(.type=="PushEvent") | {before: .payload.before, head: .payload.head}'

# before 커밋 SHA로 복구
git push --force origin BEFORE_SHA:refs/heads/main
```

### 4-3. 예방 설정

```bash
# 1. main/master에 force push 금지 (개인 설정)
git config --global alias.pushf '!f() { \
  branch=$(git rev-parse --abbrev-ref HEAD); \
  if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then \
    echo "ERROR: force push to $branch is blocked"; \
    exit 1; \
  fi; \
  git push --force-with-lease "$@"; \
}; f'

# 2. --force-with-lease 항상 사용 (다른 사람 커밋 보호)
git push --force-with-lease origin feature-branch

# 3. GitHub Branch Protection Rules 설정
# Settings > Branches > Branch protection rules
# - Require pull request reviews
# - Do not allow force pushes
# - Require status checks to pass
```

```mermaid
graph LR
    PUSH["force push 사고"] --> LOCAL{"로컬 reflog?"}
    LOCAL -->|있음| REFLOG["reflog 복구"]
    LOCAL -->|없음| TEAM{"팀원 로컬?"}
    TEAM -->|있음| CLONE["팀원 push"]
    TEAM -->|없음| EVENT["GitHub 이벤트"]
    EVENT --> RESTORE["SHA로 복구"]
```

---

## 5. 깨진 리포 복구

### 5-1. 증상 및 원인

리포가 깨지는 주된 원인:
- 디스크 장애로 `.git/objects` 파일 손상
- 시스템 크래시 중 `git gc` 실행
- 네트워크 파일 시스템(NFS, SMB)에서 동시 접근
- 강제 종료로 인덱스 파일 손상

> **비유**: 깨진 리포는 도서관에 화재가 나서 일부 서가의 책이 타버린 상황이다. `git fsck`는 화재 피해 조사관으로 어떤 책이 손상되었는지 목록을 만들고, `git recover`는 복원 전문가로 남은 파편에서 최대한 복구한다.

### 5-2. 진단

```bash
# 1. 객체 무결성 검사
git fsck --full --no-dangling
# 출력 예시:
# error: sha1 mismatch abc123...
# missing blob def456...
# broken link from tree 789abc...

# 2. 손상 범위 확인
git fsck --name-objects 2>&1 | tee fsck-report.txt

# 3. 인덱스 파일 검사
git status  # 인덱스 손상 시 에러 발생
```

### 5-3. 복구 단계

```bash
# Step 1: 인덱스 손상 시 재생성
rm .git/index
git reset

# Step 2: 특정 객체 손상 시 원격에서 복구
git fetch origin
# fetch는 로컬에 없는 객체를 다운로드

# Step 3: pack 파일 손상 시
cd .git
mv objects/pack objects/pack.bak
git unpack-objects < objects/pack.bak/*.pack
# 손상되지 않은 객체만 풀림

# Step 4: HEAD 참조 손상 시
# .git/HEAD가 깨진 경우
echo "ref: refs/heads/main" > .git/HEAD

# Step 5: 최후의 수단 — 새로 클론 후 작업 복사
git clone https://github.com/company/repo.git repo-fresh
# 기존 작업 디렉토리의 변경 파일만 복사
```

### 5-4. dangling object 복구

```bash
# dangling commit 찾기 (잃어버린 커밋)
git fsck --lost-found
# .git/lost-found/commit/ 에 복구된 커밋 SHA 목록

# 내용 확인
git show SHA_HERE

# 복구할 커밋을 브랜치로 만들기
git branch recovered-work SHA_HERE

# dangling blob 복구 (커밋되지 않은 파일)
ls .git/lost-found/other/
git show SHA_HERE > recovered-file.txt
```

---

## 6. .gitignore 문제 해결

### 6-1. 흔한 문제들

> **비유**: .gitignore는 도서관 반입 금지 목록이다. 하지만 이미 반입된 물건(이미 추적 중인 파일)에는 적용되지 않는다. 금지 목록에 "음식"을 추가해도 이미 서가에 놓인 도시락은 치워지지 않는다.

**가장 흔한 실수 — 이미 추적 중인 파일에 .gitignore 추가:**

```bash
# 문제: .env를 .gitignore에 추가했는데 여전히 추적됨
echo ".env" >> .gitignore  # 이것만으로는 부족

# 해결: 캐시에서 제거 (파일은 보존)
git rm --cached .env
git commit -m "Stop tracking .env"

# 디렉토리 전체
git rm -r --cached node_modules/
git commit -m "Stop tracking node_modules"
```

### 6-2. 패턴 디버깅

```bash
# 특정 파일이 왜 무시되는지 / 안 되는지 확인
git check-ignore -v path/to/file
# 출력: .gitignore:3:*.log  path/to/file

# 무시되는 파일 전체 목록
git status --ignored

# .gitignore가 적용 안 될 때 체크리스트:
# 1. 파일이 이미 추적 중인가? → git rm --cached
# 2. 패턴에 오타가 없는가? → git check-ignore -v
# 3. 하위 디렉토리 .gitignore가 오버라이드하는가?
# 4. .git/info/exclude에 설정이 있는가?
# 5. global gitignore가 간섭하는가?
git config --global core.excludesfile  # 글로벌 설정 확인
```

### 6-3. 글로벌 .gitignore 설정

```bash
# 모든 리포에 공통 적용할 패턴
git config --global core.excludesfile ~/.gitignore_global

# ~/.gitignore_global 예시
# OS 파일
.DS_Store
Thumbs.db

# IDE 파일
.idea/
.vscode/
*.swp

# 환경 파일
.env
.env.local
```

---

## 7. 서브모듈 트러블슈팅

### 7-1. 서브모듈 기본 이해

> **비유**: 서브모듈은 도서관 안의 "위탁 운영 코너"다. 메인 도서관(부모 리포)이 위탁 코너(서브모듈)의 현재 전시 목록(커밋 SHA)만 기록하고, 실제 운영은 별도 관리자(별도 리포)가 담당한다. 전시 목록이 어긋나면 "내가 기억하는 전시와 실제 전시가 다르다"는 오류가 발생한다.

```mermaid
graph LR
    PARENT["부모 리포"] -->|SHA 기록| SUB["서브모듈 A"]
    PARENT -->|SHA 기록| SUB2["서브모듈 B"]
    SUB -->|실제 리포| REMOTE["원격 리포 A"]
    SUB2 -->|실제 리포| REMOTE2["원격 리포 B"]
```

### 7-2. 흔한 문제와 해결

**문제 1: 클론 후 서브모듈 디렉토리가 비어 있음**

```bash
# 원인: 서브모듈은 기본적으로 자동 초기화되지 않음
# 해결:
git submodule init
git submodule update

# 또는 클론 시 한 번에:
git clone --recurse-submodules https://github.com/company/repo.git
```

**문제 2: 서브모듈이 detached HEAD 상태**

```bash
# 원인: 서브모듈은 특정 커밋 SHA를 체크아웃하므로 항상 detached HEAD
# 서브모듈에서 작업하려면 브랜치 생성:
cd submodule-dir
git checkout main
# 작업 후 부모 리포에서:
cd ..
git add submodule-dir
git commit -m "Update submodule to latest"
```

**문제 3: 서브모듈 URL 변경**

```bash
# .gitmodules 파일 수정 후:
git submodule sync --recursive
git submodule update --init --recursive
```

**문제 4: 서브모듈 완전 제거**

```bash
# 단순 rm으로는 제거 불가 — 3군데를 정리해야 함
# 1. .gitmodules에서 해당 항목 삭제
git config -f .gitmodules --remove-section submodule.path/to/sub

# 2. .git/config에서 해당 항목 삭제
git config --remove-section submodule.path/to/sub

# 3. 파일 시스템에서 제거
git rm --cached path/to/sub
rm -rf path/to/sub
rm -rf .git/modules/path/to/sub

# 4. 커밋
git commit -m "Remove submodule path/to/sub"
```

---

## 8. 느린 Git 성능 개선

### 8-1. 진단

```bash
# Git 명령 실행 시간 측정
GIT_TRACE_PERFORMANCE=1 git status

# 리포 통계 확인
git count-objects -vH
# 출력 예시:
# count: 0
# size: 0 bytes
# in-pack: 543210
# packs: 3
# size-pack: 2.10 GiB   ← 이 값이 크면 문제
# garbage: 0
```

> **비유**: 느린 Git은 정리 안 된 서고와 같다. 반납된 책이 카운터에 쌓여 있고(loose objects), 서가 분류 색인(pack index)이 오래되었고, 새 책이 들어올 때마다 전체 서가를 스캔한다. 정리(gc), 색인 갱신(commit-graph), 변경 감시(FSMonitor) 세 가지로 해결한다.

### 8-2. gc (Garbage Collection)

```bash
# 기본 gc (loose objects 정리, 불필요 객체 제거)
git gc

# 공격적 gc (느리지만 최적 압축 — 마이그레이션 후 1회 실행)
git gc --aggressive --prune=now

# gc 자동 실행 임계값 설정
git config gc.auto 256          # loose object 256개마다 자동 gc
git config gc.autoPackLimit 50  # pack 50개마다 자동 repack
```

### 8-3. git maintenance (Git 2.30+)

```bash
# 백그라운드 자동 유지보수 활성화
git maintenance start

# 수행하는 작업:
# - prefetch: 원격 객체 미리 가져오기 (1시간마다)
# - commit-graph: 커밋 그래프 캐시 갱신 (1시간마다)
# - incremental-repack: 점진적 리팩 (매일)
# - loose-objects: loose 객체 정리 (매일)
# - gc: 가비지 컬렉션 (2주마다)

# 수동 실행
git maintenance run --task=commit-graph
git maintenance run --task=gc

# 비활성화
git maintenance stop
```

### 8-4. commit-graph

10만 커밋이 넘는 리포에서 `git log`, `git merge-base` 등이 느릴 때 극적인 효과가 있다.

```bash
# commit-graph 생성 (읽기 전용 캐시)
git commit-graph write --reachable

# 점진적 업데이트 (기존 그래프에 추가)
git commit-graph write --reachable --split

# 설정으로 자동 갱신
git config core.commitGraph true
git config fetch.writeCommitGraph true
```

### 8-5. FSMonitor (파일 시스템 모니터)

대규모 리포에서 `git status`가 느린 이유는 전체 워킹 트리를 스캔하기 때문이다. FSMonitor는 OS의 파일 변경 알림을 받아 변경된 파일만 확인한다.

```bash
# 내장 FSMonitor 활성화 (Git 2.37+)
git config core.fsmonitor true
git config core.untrackedCache true

# Watchman 사용 (대규모 리포에서 더 안정적)
# Facebook이 개발한 파일 감시 데몬
git config core.fsmonitor "$(which watchman)"
```

**극한 시나리오 — 모노레포 성능 최적화 (파일 10만 개+):**

```bash
# 1. 종합 최적화 적용
git config core.fsmonitor true
git config core.untrackedCache true
git config core.commitGraph true
git config fetch.writeCommitGraph true
git config index.threads true

# 2. commit-graph 생성
git commit-graph write --reachable --split

# 3. 유지보수 자동화
git maintenance start

# 4. 효과 측정
time git status  # 최적화 전후 비교
# 일반적으로 5-10초 → 0.5초 이하로 개선
```

```mermaid
graph LR
    SLOW["느린 Git"] --> GC["gc: 객체 정리"]
    SLOW --> CG["commit-graph"]
    SLOW --> FSM["FSMonitor"]
    GC --> FAST["빠른 Git"]
    CG --> FAST
    FSM --> FAST
```

---

## 9. 실무 사고 사례 TOP 5

### 사례 1: 프로덕션 DB 비밀번호 GitHub Public 리포에 노출

**상황**: 신입 개발자가 `application.yml`에 프로덕션 DB 비밀번호를 하드코딩하고 public 리포에 push. GitHub 자동 스캔이 감지하기 전에 봇이 이미 크롤링.

**원인**: `.gitignore`에 `application.yml` 미등록, pre-commit 훅 미설정, 환경변수 미사용

**해결 과정:**

```bash
# Step 1 (T+0분): DB 비밀번호 즉시 변경
# DBA에게 연락하여 프로덕션 DB 비밀번호 로테이션

# Step 2 (T+5분): 접근 로그 확인
# DB 서버에서 비정상 접근 로그 확인

# Step 3 (T+10분): 히스토리에서 제거
git clone --mirror https://github.com/company/repo.git
cd repo.git
git filter-repo --invert-paths --path src/main/resources/application.yml --force
git push --force --all
git push --force --tags

# Step 4 (T+30분): GitHub에 캐시 삭제 요청
# GitHub Support > Report a vulnerability > Sensitive data exposure

# Step 5: 재발 방지
# .gitignore 추가
echo "src/main/resources/application*.yml" >> .gitignore
# pre-commit 훅 설치
# 환경변수로 전환
```

**교훈**: 키 로테이션이 최우선이다. 히스토리 정리는 그 다음이다. "커밋을 지우면 안전하다"는 착각이 가장 위험하다.

---

### 사례 2: main 브랜치 force push로 2주치 커밋 소실

**상황**: 개발자가 로컬 main을 rebase하고 습관적으로 `git push --force` 실행. 팀원 15명의 2주간 커밋 200개가 원격에서 사라짐.

**원인**: branch protection 미설정, `--force` 대신 `--force-with-lease` 미사용

**해결 과정:**

```bash
# Step 1: 팀 전체에 "git fetch/pull 금지" 공지
# 누군가 fetch하면 reflog의 이전 origin/main이 덮어써짐

# Step 2: 사고 발생자 PC에서 reflog 확인
git reflog show origin/main
# origin/main@{1}: 사고 이전 SHA 확인

# Step 3: 원래 커밋으로 복구
git push --force origin ORIGINAL_SHA:refs/heads/main

# Step 4: 모든 팀원에게 git fetch 허용

# Step 5: 예방 조치
# GitHub Branch Protection Rule:
# - Require pull request reviews before merging
# - Do not allow force pushes
# - Include administrators
```

**교훈**: Branch Protection은 선택이 아니라 필수다. 관리자도 예외 없이 적용해야 한다.

---

### 사례 3: git gc 중 시스템 크래시로 리포 손상

**상황**: 대규모 리포에서 `git gc --aggressive` 실행 중 서버 정전. 이후 모든 git 명령이 "corrupt pack file" 에러 발생.

**원인**: gc 중 pack 파일 재작성 과정에서 중단됨

**해결 과정:**

```bash
# Step 1: 손상 범위 파악
git fsck --full 2>&1 | tee fsck-report.txt
# error: corrupt pack file .git/objects/pack/pack-xxx.pack

# Step 2: 손상된 pack 이동
mkdir -p .git/objects/pack.bak
mv .git/objects/pack/pack-xxx.* .git/objects/pack.bak/

# Step 3: 원격에서 객체 복구
git fetch origin

# Step 4: 무결성 재검증
git fsck --full
# 에러 없으면 성공

# Step 5: 남은 loose objects 정리
git gc --prune=now
```

**교훈**: NFS/네트워크 파일시스템에서는 `git gc --aggressive`를 피하라. UPS(무정전 전원장치) 없는 서버에서 대규모 gc는 위험하다.

---

### 사례 4: 서브모듈 버전 불일치로 CI/CD 빌드 실패

**상황**: 모노레포의 서브모듈을 업데이트했으나 부모 리포에서 서브모듈 SHA를 커밋하지 않음. CI에서 이전 버전 서브모듈로 빌드되어 호환성 에러 발생.

**원인**: 서브모듈 업데이트 후 부모 리포에서 `git add submodule-dir && git commit` 누락

**해결 과정:**

```bash
# Step 1: 서브모듈 상태 확인
git submodule status
# +abc1234 libs/shared-utils (heads/main) ← + 표시 = 부모가 기록한 SHA와 다름

# Step 2: 부모 리포에서 서브모듈 SHA 갱신
git add libs/shared-utils
git commit -m "Update shared-utils submodule to latest"
git push

# Step 3: CI/CD에서 서브모듈 자동 초기화 설정
# .github/workflows/build.yml
# steps:
#   - uses: actions/checkout@v4
#     with:
#       submodules: recursive
```

**교훈**: 서브모듈은 "자동"이 아니다. 업데이트할 때마다 부모 리포에서 명시적으로 커밋해야 한다. CI 파이프라인에 `submodules: recursive` 설정은 필수다.

---

### 사례 5: .gitignore 없이 node_modules 커밋으로 리포 5GB 폭증

**상황**: 프론트엔드 프로젝트에서 `.gitignore`를 설정하지 않고 6개월간 개발. `node_modules` (2GB)와 `.next` 빌드 캐시(1GB)가 히스토리에 축적되어 리포가 5GB를 돌파. 클론에 20분 소요.

**원인**: 프로젝트 초기 `.gitignore` 생성 누락

**해결 과정:**

```bash
# Step 1: 용량 분석
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | sort -rnk2 | head -20

# Step 2: 히스토리에서 제거
pip install git-filter-repo
git filter-repo --invert-paths \
  --path node_modules/ \
  --path .next/ \
  --path dist/ \
  --force

# Step 3: 리포 정리
git reflog expire --expire=now --all
git gc --aggressive --prune=now
# 5GB → 50MB로 감소

# Step 4: .gitignore 추가
curl -o .gitignore https://raw.githubusercontent.com/github/gitignore/main/Node.gitignore
git add .gitignore
git commit -m "Add .gitignore for Node.js"

# Step 5: 원격 강제 푸시 (팀 공지 후)
git push --force origin main
# 모든 팀원 reclone 필요
```

**교훈**: 프로젝트 첫 커밋은 `.gitignore`여야 한다. `gitignore.io` 또는 GitHub 템플릿을 사용하면 30초면 설정된다.

---

## 10. 종합 트러블슈팅 플로우차트

문제가 발생했을 때 어디서부터 접근해야 할지 판단하는 의사결정 트리이다.

```mermaid
graph LR
    START["Git 문제 발생"] --> TYPE{"문제 유형?"}
    TYPE -->|충돌| MERGE["3-way merge"]
    TYPE -->|느림| PERF["gc + FSMonitor"]
    TYPE -->|유출| KEY["키 로테이션 우선"]
    TYPE -->|손상| FSCK["git fsck"]
    TYPE -->|용량| LFS["LFS + filter-repo"]
```

---

## 11. 면접 포인트

<details>
<summary><strong>Q1. 3-way merge와 2-way merge의 차이점과 장단점을 설명해 주세요.</strong></summary>

**핵심 답변:**

2-way merge는 두 파일만 비교하므로 "원래 내용이 무엇이었는지" 알 수 없다. 따라서 양쪽이 같은 줄을 수정하지 않았더라도, base와 달라진 모든 줄이 충돌로 표시된다.

3-way merge는 공통 조상(base)을 함께 비교한다. base에서 한쪽만 변경한 줄은 자동으로 변경된 쪽을 채택하고, 양쪽 모두 다르게 변경한 줄만 충돌로 표시한다. 이 덕분에 충돌 빈도가 극적으로 줄어든다.

Git이 3-way merge를 채택한 이유는 분산 버전 관리에서 수많은 브랜치가 동시에 작업되므로, 자동 병합 성공률을 최대화하는 것이 핵심이기 때문이다.

**꼬리 질문 대비:**
- recursive merge strategy: 공통 조상이 여러 개일 때 가상의 merge base를 만들어 3-way merge 수행
- `git rerere`: 한번 해결한 충돌 패턴을 기록하여 동일 충돌 자동 해결
- `rebase` 중 ours/theirs가 뒤바뀌는 이유: rebase는 대상 브랜치 위에 커밋을 재적용하므로 관점이 반전됨

</details>

<details>
<summary><strong>Q2. Git LFS의 동작 원리와 일반 Git 저장과의 차이를 설명해 주세요.</strong></summary>

**핵심 답변:**

일반 Git은 모든 파일의 전체 내용을 blob 객체로 저장한다. 100MB 바이너리가 10번 변경되면 히스토리에 1GB가 쌓인다 (delta 압축이 되지만 바이너리는 효율이 낮다).

Git LFS는 대용량 파일의 실제 내용을 별도 LFS 서버에 저장하고, Git 리포에는 SHA-256 해시와 크기만 기록한 포인터 파일(약 130바이트)을 저장한다. `checkout` 시 clean/smudge 필터를 통해 포인터를 실제 파일로 교체한다.

포인터 파일 구조:
```
version https://git-lfs.github.com/spec/v1
oid sha256:4d7a214614...
size 104857600
```

**장단점:**
- 장점: 리포 크기 극적 감소, 클론 속도 향상, 히스토리 순회 빠름
- 단점: LFS 서버 필요, 오프라인 작업 제한, GitHub LFS 스토리지 요금

**꼬리 질문 대비:**
- `git lfs migrate import`: 기존 히스토리의 바이너리를 LFS로 변환 (히스토리 재작성)
- LFS locking: 바이너리 파일 동시 편집 방지 기능
- 대안: Git Annex (더 유연하지만 복잡), DVC (ML 모델 특화)

</details>

<details>
<summary><strong>Q3. 비밀키가 Git 히스토리에 커밋된 것을 발견했을 때 대응 절차를 설명해 주세요.</strong></summary>

**핵심 답변:**

**1순위: 키 로테이션** — 히스토리 정리보다 키 무효화가 먼저다. 커밋이 남아 있는 동안 누군가 이미 키를 탈취했을 수 있기 때문이다.

**2순위: 영향 분석** — 해당 키로 접근 가능한 시스템과 데이터 범위 파악. 침해 흔적(비정상 API 호출, DB 접근 로그) 확인.

**3순위: 히스토리 정리** — `git filter-repo`로 해당 파일/문자열을 전체 히스토리에서 제거. `git filter-branch`는 deprecated이므로 사용하지 않는다. BFG Repo-Cleaner도 대안이지만 filter-repo가 더 범용적이다.

**4순위: 예방 체계 구축** — pre-commit 훅(detect-secrets, git-secrets), `.gitignore` 강화, 환경변수/Vault 사용으로 전환.

**주의점:** GitHub에서 커밋을 force push로 제거해도 PR, 이슈 코멘트, fork에 캐시가 남을 수 있다. GitHub Support에 별도 삭제 요청이 필요하다. 또한 Google 캐시, Wayback Machine에도 남을 수 있으므로 키 로테이션이 유일한 완전한 대응이다.

</details>

<details>
<summary><strong>Q4. 모노레포에서 Git 성능을 최적화하는 방법을 설명해 주세요.</strong></summary>

**핵심 답변:**

모노레포에서 성능 저하가 발생하는 3대 병목:

**1. `git status` 느림** — 전체 워킹 트리 스캔이 원인. FSMonitor(`core.fsmonitor=true`)를 활성화하면 OS 파일 변경 알림만 확인하므로 10만 파일 기준 5초 이상 → 0.5초 이하로 개선된다.

**2. `git log` / `git merge-base` 느림** — 10만 커밋 순회가 원인. commit-graph(`core.commitGraph=true`)를 활성화하면 커밋 간 관계를 바이너리 캐시로 조회하여 O(n) → O(1)에 가까운 성능을 얻는다.

**3. 클론/fetch 느림** — 전체 객체 다운로드가 원인. Partial Clone(`--filter=blob:none`)과 Sparse Checkout(`--sparse`)을 조합하면 필요한 디렉토리의 객체만 지연 로딩한다.

추가로 `git maintenance start`를 설정하면 prefetch, commit-graph 갱신, incremental-repack, gc를 백그라운드에서 자동 수행한다.

**꼬리 질문 대비:**
- Google은 자체 VFS(Virtual File System)를 사용, Microsoft는 Scalar(구 VFS for Git)를 개발
- `index.threads=true`: 인덱스 로딩을 멀티스레드로 처리
- `feature.manyFiles=true`: 대규모 리포에 적합한 설정 묶음 활성화

</details>

<details>
<summary><strong>Q5. force push 사고가 발생했을 때 복구 절차와 예방 방법을 설명해 주세요.</strong></summary>

**핵심 답변:**

**복구 우선순위:**

1. **팀 전체에 fetch/pull 금지 공지** — 로컬 reflog이 유일한 복구 수단인데, fetch하면 덮어써진다.
2. **사고 발생자 로컬에서 reflog 확인** — `git reflog show origin/main`으로 force push 직전 SHA를 찾는다.
3. **원래 커밋으로 force push** — `git push --force origin ORIGINAL_SHA:refs/heads/main`
4. 로컬 reflog이 없으면 다른 팀원의 로컬, GitHub Events API, 또는 GitHub Support에서 복구한다.

**예방 방법:**

- **`--force-with-lease`** — 원격 브랜치가 내가 마지막으로 fetch한 것과 같을 때만 force push를 허용. 다른 사람의 커밋을 덮어쓰는 것을 방지.
- **Branch Protection Rule** — main/master에 force push 금지, 관리자 포함.
- **alias 설정** — `git pushf`를 만들어 main 브랜치에서는 자동 차단하고, 항상 `--force-with-lease`를 사용하도록 설정.

**`--force`와 `--force-with-lease`의 차이:**
- `--force`: 무조건 덮어쓰기. 다른 사람 커밋도 삭제됨.
- `--force-with-lease`: 마지막 fetch 이후 원격이 변경되었으면 거부. 안전한 force push.

</details>

---

## 참고 자료

| 자료 | 설명 |
|------|------|
| [Pro Git Book](https://git-scm.com/book/ko) | 공식 한국어 번역 교재 |
| [git filter-repo](https://github.com/newren/git-filter-repo) | filter-branch 대체 도구 |
| [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) | 히스토리 정리 도구 |
| [Git LFS](https://git-lfs.github.com/) | 대용량 파일 관리 |
| [GitHub gitignore templates](https://github.com/github/gitignore) | 언어/프레임워크별 .gitignore |
| [detect-secrets](https://github.com/Yelp/detect-secrets) | 비밀키 탐지 pre-commit 훅 |
| [Scalar](https://github.com/microsoft/scalar) | Microsoft의 대규모 리포 도구 |
