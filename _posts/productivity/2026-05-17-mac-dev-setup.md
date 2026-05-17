---
layout: single
title: "macOS 개발환경 완벽 세팅 — 신규 입사 첫날 2시간 만에 끝내기"
date: 2026-05-17 10:00:00 +0900
categories: PRODUCTIVITY
tags: [macOS, 개발환경, Homebrew, iTerm2, 세팅, 설치]
toc: true
toc_sticky: true
toc_label: 목차
---

새 맥북을 받았을 때의 설렘은 잠깐이고, 그 다음에는 긴 설치 노동이 시작됩니다. Homebrew, 터미널, Java, Node, Docker, IDE... 하나씩 찾아가며 설치하다 보면 반나절이 금방 지나갑니다. 이 가이드 하나로 순서대로 따라가면 **2시간 안에 완전한 백엔드 개발환경**을 갖출 수 있습니다.

---

## 0. 시작 전 준비

### macOS 업데이트 확인

모든 설치 전에 macOS를 최신 버전으로 업데이트합니다.

```
Apple 메뉴 → 시스템 설정 → 소프트웨어 업데이트
```

### Xcode Command Line Tools

대부분의 개발 도구가 이것을 요구합니다. 제일 먼저 설치합니다.

```bash
xcode-select --install
```

팝업이 뜨면 "설치" 클릭. 완료까지 5-10분 소요.

> **비유:** Xcode Command Line Tools는 집 공사를 시작하기 전에 갖춰야 하는 기본 공구 세트입니다. 이게 없으면 다른 어떤 도구도 제대로 작동하지 않습니다.

---

## 1. Homebrew — macOS 패키지 매니저

Homebrew는 macOS의 패키지 매니저입니다. 앞으로 거의 모든 소프트웨어를 Homebrew로 설치합니다.

> **비유:** Homebrew는 앱스토어처럼 소프트웨어를 설치하지만, 개발자 도구에 특화되어 있고 명령어 한 줄로 설치/삭제/업데이트가 가능합니다.

### 1.1 Homebrew 설치

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Apple Silicon(M1/M2/M3) 맥 추가 설정:**
```bash
# .zprofile에 Homebrew PATH 추가
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 1.2 설치 확인

```bash
brew --version
# Homebrew 4.x.x 출력되면 성공
```

### 1.3 Homebrew 기본 명령어

```bash
brew install [패키지]    # 설치
brew uninstall [패키지]  # 제거
brew upgrade [패키지]    # 업그레이드
brew list               # 설치된 패키지 목록
brew search [키워드]     # 패키지 검색
brew info [패키지]       # 패키지 정보
brew update             # Homebrew 자체 업데이트
brew cleanup            # 오래된 버전 삭제
```

---

## 2. iTerm2 + Oh My Zsh — 터미널 환경

기본 터미널로도 개발이 가능하지만, iTerm2 + Oh My Zsh 조합은 개발자 경험을 완전히 다른 차원으로 올려줍니다.

### 2.1 iTerm2 설치

```bash
brew install --cask iterm2
```

### 2.2 iTerm2 기본 설정

**Preferences → Profiles → Colors:**
- Color Presets: "Solarized Dark" 또는 "Dracula" 선택

**Preferences → Profiles → Text:**
- Font: "MesloLGS NF" 또는 "Hack Nerd Font" (아래에서 설치)
- Font Size: 14

**Preferences → General → Closing:**
- "Confirm 'Quit iTerm2'" 체크 해제 (실수로 끄는 것 방지)

### 2.3 Nerd Font 설치

```bash
brew tap homebrew/cask-fonts
brew install --cask font-meslo-lg-nerd-font
```

### 2.4 Oh My Zsh 설치

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

### 2.5 Powerlevel10k 테마 (선택, 강력 추천)

```bash
# Powerlevel10k 설치
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
  ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k

# .zshrc 수정
# ZSH_THEME="robbyrussell" → ZSH_THEME="powerlevel10k/powerlevel10k"
```

iTerm2를 재시작하면 Powerlevel10k 설정 마법사가 실행됩니다.

### 2.6 필수 Oh My Zsh 플러그인

```bash
# zsh-autosuggestions (이전 명령어 자동 제안)
git clone https://github.com/zsh-users/zsh-autosuggestions \
  ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# zsh-syntax-highlighting (명령어 색상 표시)
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \
  ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
```

**.zshrc에서 플러그인 활성화:**
```bash
plugins=(
  git
  zsh-autosuggestions
  zsh-syntax-highlighting
  docker
  gradle
  mvn
  kubectl
)
```

### 2.7 유용한 .zshrc 설정

```bash
# ~/.zshrc 하단에 추가

# 히스토리 설정
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_DUPS
setopt SHARE_HISTORY

# 유용한 alias
alias ll="ls -alF"
alias la="ls -A"
alias l="ls -CF"
alias ..="cd .."
alias ...="cd ../.."
alias gs="git status"
alias gl="git log --oneline -20 --graph"
alias gd="git diff"
alias gc="git commit"
alias gp="git push"
alias ports="lsof -i -P -n | grep LISTEN"

# 프로젝트 디렉터리
export PROJECTS="$HOME/projects"
alias proj="cd $PROJECTS"
```

```bash
# 변경사항 적용
source ~/.zshrc
```

---

## 3. Git 설정

### 3.1 기본 설정

```bash
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"
git config --global core.editor "vim"
git config --global init.defaultBranch main
git config --global pull.rebase false
```

### 3.2 SSH 키 생성 및 GitHub 등록

```bash
# SSH 키 생성 (Ed25519 알고리즘, 더 안전)
ssh-keygen -t ed25519 -C "hong@example.com"

# 기본 위치(~/.ssh/id_ed25519)에 저장, passphrase 설정 권장

# SSH 에이전트에 키 추가
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 공개키 클립보드에 복사
pbcopy < ~/.ssh/id_ed25519.pub
```

GitHub → Settings → SSH and GPG keys → New SSH key → 붙여넣기

```bash
# 연결 테스트
ssh -T git@github.com
# "Hi username! You've successfully authenticated" 출력되면 성공
```

### 3.3 유용한 Git 설정

```bash
# ~/.gitconfig 추가 설정

[core]
    autocrlf = input
    safecrlf = true

[color]
    ui = auto

[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    lg = log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit
    undo = reset --soft HEAD~1
    amend = commit --amend --no-edit

[push]
    default = current
```

---

## 4. Java 개발환경 — SDKMAN

Java 개발자라면 SDKMAN이 필수입니다. 여러 Java 버전을 쉽게 전환할 수 있습니다.

> **비유:** SDKMAN은 Java 버전의 "옷장" 같은 것입니다. 옷장에 여러 옷을 걸어두고 오늘 어떤 옷을 입을지 선택하는 것처럼, 여러 Java 버전을 설치해두고 프로젝트마다 다른 버전을 사용합니다.

### 4.1 SDKMAN 설치

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# 설치 확인
sdk version
```

### 4.2 Java 설치

```bash
# 설치 가능한 Java 버전 목록
sdk list java

# Java 17 LTS 설치 (Temurin 권장)
sdk install java 17.0.10-tem

# Java 21 LTS 설치
sdk install java 21.0.2-tem

# 기본 버전 설정
sdk default java 17.0.10-tem

# 현재 세션만 다른 버전 사용
sdk use java 21.0.2-tem

# 설치 확인
java -version
```

### 4.3 프로젝트별 Java 버전 관리

```bash
# 프로젝트 루트에 .sdkmanrc 파일 생성
echo "java=17.0.10-tem" > .sdkmanrc

# 해당 디렉터리 진입 시 자동 전환 (설정 필요)
# ~/.sdkman/etc/config에서
# sdkman_auto_env=true 설정
```

### 4.4 Gradle 설치

```bash
sdk install gradle 8.5

gradle --version
```

### 4.5 Maven 설치

```bash
sdk install maven 3.9.6

mvn --version
```

---

## 5. Node.js — NVM

Node.js도 버전 관리가 중요합니다. NVM(Node Version Manager)을 사용합니다.

### 5.1 NVM 설치

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# .zshrc에 자동으로 추가되지만, 확인 후 없으면 수동 추가
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

source ~/.zshrc

# 확인
nvm --version
```

### 5.2 Node.js 설치

```bash
# LTS 버전 설치 (권장)
nvm install --lts
nvm use --lts
nvm alias default node

# 특정 버전 설치
nvm install 20.11.0
nvm install 18.19.0

# 설치된 버전 목록
nvm ls

# 버전 전환
nvm use 18

# 확인
node --version
npm --version
```

### 5.3 전역 패키지 설치

```bash
# 자주 쓰는 전역 패키지
npm install -g pnpm        # 빠른 패키지 매니저
npm install -g yarn        # 또 다른 패키지 매니저
npm install -g typescript  # TypeScript 컴파일러
npm install -g ts-node     # TypeScript 직접 실행
npm install -g nodemon     # 파일 변경 시 자동 재시작
npm install -g http-server # 간단한 HTTP 서버
```

---

## 6. Docker

Docker는 개발 환경을 컨테이너로 격리해서, "내 컴퓨터에서는 되는데"를 없애줍니다.

> **비유:** Docker는 음식 배달 용기와 같습니다. 요리사(개발자)가 만든 음식(앱)을 용기(컨테이너)에 담으면, 어떤 환경에서도 동일한 상태로 배달됩니다.

### 6.1 Docker Desktop 설치

```bash
brew install --cask docker
```

설치 후 애플리케이션에서 Docker Desktop 실행. 시스템 트레이에 고래 아이콘이 보이면 성공.

### 6.2 Docker 설정 최적화

Docker Desktop → Settings:

```
Resources:
- CPUs: 전체의 50% (예: 4코어면 2)
- Memory: 4-8GB (전체 RAM의 50%)
- Disk image size: 60GB

General:
- "Start Docker Desktop when you log in" 체크
- "Use Docker Compose V2" 체크
```

### 6.3 개발용 Docker Compose

자주 쓰는 로컬 개발 인프라를 docker-compose로 관리합니다.

```yaml
# ~/dev-infra/docker-compose.yml

version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: dev-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: devdb
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    container_name: dev-redis
    ports:
      - "6379:6379"
    command: redis-server --requirepass devpass

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: dev-kafka
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: dev-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

volumes:
  mysql-data:
```

```bash
# 모든 서비스 시작
cd ~/dev-infra && docker-compose up -d

# 개별 서비스 시작
docker-compose up -d mysql redis

# 중지
docker-compose down

# 편리한 alias 추가
alias devup="cd ~/dev-infra && docker-compose up -d"
alias devdown="cd ~/dev-infra && docker-compose down"
```

---

## 7. IDE 설치

### 7.1 IntelliJ IDEA

```bash
brew install --cask intellij-idea
# 또는 커뮤니티 에디션 (무료)
brew install --cask intellij-idea-ce
```

**필수 플러그인 (Preferences → Plugins):**

```
- Lombok: Lombok 어노테이션 지원
- SonarLint: 코드 품질 분석
- GitToolBox: Git 상태 표시 향상
- Rainbow Brackets: 괄호 색상 구분
- String Manipulation: 문자열 변환 도구
- HTTP Client: REST API 테스트
- Docker: Docker 통합
- Kubernetes: K8s 지원
- .env files support: .env 파일 지원
```

**IntelliJ 성능 최적화:**

```
# Help → Edit Custom VM Options
-Xms1g
-Xmx4g
-XX:+UseG1GC
```

### 7.2 VS Code / Cursor

```bash
# VS Code
brew install --cask visual-studio-code

# Cursor (AI 네이티브 에디터)
brew install --cask cursor
```

**VS Code 필수 확장:**

```bash
# 명령어로 일괄 설치
code --install-extension esbenp.prettier-vscode
code --install-extension dbaeumer.vscode-eslint
code --install-extension eamodio.gitlens
code --install-extension ms-vscode.vscode-typescript-next
code --install-extension bradlc.vscode-tailwindcss
code --install-extension ms-azuretools.vscode-docker
code --install-extension redhat.vscode-yaml
code --install-extension ms-vscode-remote.remote-ssh
```

---

## 8. DB 클라이언트

### 8.1 DBeaver (무료, 다목적)

```bash
brew install --cask dbeaver-community
```

MySQL, PostgreSQL, Oracle, SQLite 등 모든 DB를 하나의 도구로 관리합니다.

### 8.2 TablePlus (유료, macOS 최적화)

```bash
brew install --cask tableplus
```

macOS 네이티브 앱으로 빠르고 깔끔한 UI를 제공합니다.

### 8.3 Redis CLI 도구

```bash
# RedisInsight (GUI)
brew install --cask redisinsight

# CLI 도구
brew install redis
# redis-cli 명령어 사용 가능
```

---

## 9. 유틸리티 도구

### 9.1 개발자 필수 유틸리티

```bash
# Raycast (런처, Alfred 대안)
brew install --cask raycast

# Rectangle (창 관리)
brew install --cask rectangle

# CleanShot X (스크린샷, 유료 대안: Monosnap)
brew install --cask monosnap

# 1Password (비밀번호 관리)
brew install --cask 1password

# Postman (API 테스트)
brew install --cask postman

# Insomnia (API 테스트, 대안)
brew install --cask insomnia

# Charles (HTTP 디버깅 프록시)
brew install --cask charles

# Proxyman (HTTP 디버깅, macOS 최적화)
brew install --cask proxyman
```

### 9.2 커맨드라인 유틸리티

```bash
# jq: JSON 처리
brew install jq

# httpie: curl 대안 (더 읽기 쉬운 HTTP 클라이언트)
brew install httpie

# fzf: 퍼지 검색
brew install fzf
$(brew --prefix)/opt/fzf/install

# bat: cat 대안 (문법 하이라이팅)
brew install bat
alias cat="bat"

# eza: ls 대안 (색상, 아이콘)
brew install eza
alias ls="eza --icons"
alias ll="eza -alF --icons"

# fd: find 대안 (더 빠르고 간단)
brew install fd

# ripgrep: grep 대안 (훨씬 빠름)
brew install ripgrep
alias grep="rg"

# tree: 디렉터리 구조 시각화
brew install tree

# htop: top 대안
brew install htop

# tldr: man 대신 간단한 사용법 요약
brew install tldr

# gh: GitHub CLI
brew install gh
gh auth login
```

### 9.3 보안 도구

```bash
# gpg: 파일/커밋 서명
brew install gpg

# git-secrets: 민감 정보 커밋 방지
brew install git-secrets
git secrets --install
git secrets --register-aws
```

---

## 10. Kubernetes 도구 (선택)

클라우드 환경에서 작업한다면 K8s 도구를 설치합니다.

```bash
# kubectl: K8s 클러스터 관리
brew install kubectl

# kubectx + kubens: 컨텍스트/네임스페이스 전환
brew install kubectx

# Helm: K8s 패키지 매니저
brew install helm

# k9s: K8s 터미널 UI
brew install k9s

# Lens: K8s GUI (선택)
brew install --cask lens
```

---

## 11. Brewfile — 모든 것을 한 번에

Brewfile을 사용하면 위에서 설치한 모든 것을 단 한 줄 명령어로 재설치할 수 있습니다.

> **비유:** Brewfile은 식당 주방의 레시피 북과 같습니다. 어떤 주방에 가든 같은 레시피로 동일한 요리를 만들 수 있듯이, 어떤 맥북에서든 동일한 개발환경을 재현합니다.

### 11.1 현재 설치된 것으로 Brewfile 생성

```bash
brew bundle dump --file=~/Brewfile --force
```

### 11.2 표준 개발자 Brewfile

```ruby
# ~/Brewfile

# CLI 도구
brew "git"
brew "jq"
brew "httpie"
brew "fzf"
brew "bat"
brew "eza"
brew "fd"
brew "ripgrep"
brew "tree"
brew "htop"
brew "tldr"
brew "gh"
brew "gpg"

# 개발 도구
brew "sdkman"
brew "gradle"
brew "maven"

# 인프라
brew "kubectl"
brew "helm"
brew "k9s"

# 앱 (Cask)
cask "iterm2"
cask "font-meslo-lg-nerd-font"
cask "docker"
cask "intellij-idea"
cask "visual-studio-code"
cask "cursor"
cask "dbeaver-community"
cask "redisinsight"
cask "postman"
cask "raycast"
cask "rectangle"
cask "1password"
cask "proxyman"
```

### 11.3 Brewfile로 일괄 설치

```bash
# 새 맥북에서 모든 것 한 번에 설치
brew bundle install --file=~/Brewfile
```

### 11.4 Brewfile을 dotfiles 리포에 관리

```bash
# dotfiles 리포 생성
mkdir ~/dotfiles
mv ~/Brewfile ~/dotfiles/Brewfile
cd ~/dotfiles
git init
git remote add origin git@github.com:username/dotfiles.git
git add Brewfile
git commit -m "Add Brewfile"
git push -u origin main
```

---

## 12. dotfiles 관리

개발 환경 설정 파일들을 Git으로 관리하면 새 컴퓨터 세팅이 극적으로 빠르고 일관되게 됩니다.

### 12.1 관리할 파일 목록

```
dotfiles/
├── Brewfile           # Homebrew 패키지 목록
├── .zshrc             # Zsh 설정
├── .gitconfig         # Git 설정
├── .gitignore_global  # 전역 Git ignore
├── .vimrc             # Vim 설정 (선택)
└── setup.sh           # 자동 설정 스크립트
```

### 12.2 setup.sh 자동화 스크립트

```bash
#!/bin/bash
# setup.sh — 새 맥북 초기 설정 자동화

set -e

echo "🚀 개발환경 자동 설정 시작"

# Xcode CLI Tools
echo "1. Xcode CLI Tools 설치..."
xcode-select --install 2>/dev/null || echo "이미 설치됨"

# Homebrew
echo "2. Homebrew 설치..."
if ! command -v brew &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Apple Silicon 설정
if [[ $(uname -m) == 'arm64' ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Brewfile로 패키지 설치
echo "3. Brewfile 패키지 설치..."
brew bundle install --file=~/dotfiles/Brewfile

# Oh My Zsh
echo "4. Oh My Zsh 설치..."
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

# Oh My Zsh 플러그인
echo "5. Zsh 플러그인 설치..."
git clone https://github.com/zsh-users/zsh-autosuggestions \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions 2>/dev/null || true
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting 2>/dev/null || true

# dotfiles symlink 생성
echo "6. dotfiles 심볼릭 링크 생성..."
ln -sf ~/dotfiles/.zshrc ~/.zshrc
ln -sf ~/dotfiles/.gitconfig ~/.gitconfig
ln -sf ~/dotfiles/.gitignore_global ~/.gitignore_global

# SDKMAN
echo "7. SDKMAN 설치..."
if [ ! -d "$HOME/.sdkman" ]; then
    curl -s "https://get.sdkman.io" | bash
fi

# NVM
echo "8. NVM 설치..."
if [ ! -d "$HOME/.nvm" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

echo "✅ 설정 완료! 터미널을 재시작하세요."
```

### 12.3 심볼릭 링크 전략

원본 파일은 dotfiles 리포에 두고, 홈 디렉터리에는 심볼릭 링크를 만듭니다.

```bash
# 심볼릭 링크 생성
ln -sf ~/dotfiles/.zshrc ~/.zshrc
ln -sf ~/dotfiles/.gitconfig ~/.gitconfig

# 확인
ls -la ~ | grep "\->"
```

---

## 13. macOS 시스템 설정 최적화

개발자에게 유용한 macOS 설정들입니다.

### 13.1 터미널 명령으로 macOS 설정

```bash
# 파인더: 숨김 파일 표시
defaults write com.apple.finder AppleShowAllFiles YES

# 파인더: 경로 막대 표시
defaults write com.apple.finder ShowPathbar -bool true

# 파인더: 상태 막대 표시
defaults write com.apple.finder ShowStatusBar -bool true

# 스크린샷 저장 위치 변경
mkdir -p ~/Screenshots
defaults write com.apple.screencapture location ~/Screenshots

# 키 반복 속도 빠르게
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Dock 자동 숨기기
defaults write com.apple.dock autohide -bool true

# 변경사항 적용
killall Finder
killall Dock
```

### 13.2 시스템 설정 UI에서 할 것

```
키보드 → 키 반복: 빠름, 반복 전 대기 시간: 짧게
손쉬운 사용 → 포인터 제어 → 트랙패드 옵션 → 드래그 활성화: 세 손가락
트랙패드 → 탭하여 클릭 활성화
보안 → 화면 잠금: 5분
Dock → 크기: 중간, 자동 숨기기 활성화
```

---

## 14. 환경 변수 관리

### 14.1 direnv — 디렉터리별 환경 변수

```bash
brew install direnv

# .zshrc에 추가
eval "$(direnv hook zsh)"
```

```bash
# 프로젝트별 .envrc 파일
# ~/projects/myapp/.envrc
export DATABASE_URL="postgresql://localhost:5432/myapp"
export REDIS_URL="redis://localhost:6379"
export API_KEY="dev-key-12345"

# 해당 디렉터리에서 허용
direnv allow
```

### 14.2 1Password CLI — 시크릿 관리

```bash
brew install --cask 1password-cli

# 로그인
op signin

# 시크릿 주입
op run -- java -jar myapp.jar
```

---

## 15. 전체 설치 순서 요약

새 맥북을 받았을 때의 설치 순서입니다.

```
⏱ 예상 소요 시간: 약 2시간 (다운로드 속도에 따라 다름)

[1단계: 기반] 20분
□ macOS 업데이트
□ Xcode CLI Tools
□ Homebrew 설치

[2단계: 터미널] 20분
□ iTerm2 설치
□ Nerd Font 설치
□ Oh My Zsh 설치
□ Powerlevel10k 설치
□ Zsh 플러그인 설치

[3단계: Git] 10분
□ Git 설정 (이름, 이메일)
□ SSH 키 생성 및 GitHub 등록

[4단계: 언어 런타임] 20분
□ SDKMAN → Java 17, 21
□ NVM → Node.js LTS

[5단계: 인프라] 10분
□ Docker Desktop 설치 및 설정

[6단계: IDE] 20분
□ IntelliJ IDEA
□ VS Code 또는 Cursor
□ 필수 플러그인 설치

[7단계: DB 클라이언트] 10분
□ DBeaver 또는 TablePlus
□ RedisInsight

[8단계: 유틸리티] 10분
□ Raycast
□ Rectangle
□ 커맨드라인 도구 (jq, bat, eza 등)

[9단계: dotfiles] 10분
□ Brewfile 생성
□ dotfiles 리포 구성
□ 심볼릭 링크 설정
```

---

## 마치며

처음에는 2시간이 걸리지만, dotfiles와 Brewfile을 잘 구성해두면 **다음 맥북 세팅은 30분 안에** 끝낼 수 있습니다. 새 컴퓨터를 받을 때마다 처음부터 다시 설정하는 고통을 없애는 것, 그것이 dotfiles 관리의 핵심 가치입니다.

무엇보다 중요한 것은 이 가이드를 그대로 따르는 것이 아니라, 자신만의 환경을 만들어가는 것입니다. 이 가이드를 기초로 삼아, 자신의 업무에 맞게 커스터마이징해보세요.

```bash
# 마지막으로, 오늘 설정한 것들이 잘 동작하는지 확인
java -version && node -v && docker --version && git --version
```

---

*본 가이드는 macOS Sonoma 14.x + Apple Silicon 기준으로 작성되었습니다. Intel 맥에서는 Homebrew 경로가 `/usr/local`입니다.*
