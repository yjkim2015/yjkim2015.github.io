"""details 블록을 원래 마크다운 ## 극한 시나리오 헤더로 되돌린다"""
import glob, os, re

POSTS_DIR = r"C:\Users\Kim\OneDrive\문서\yjkim2015.github.io\_posts"

# details 블록 시작
DETAILS_START = re.compile(
    r'<details class="extreme-scenario-details"[^>]*>\s*'
    r'<summary class="extreme-scenario-summary">\s*'
    r'<span class="extreme-scenario-icon">[^<]*</span>\s*'
    r'<span class="extreme-scenario-label">[^<]*</span>\s*'
    r'<span class="extreme-scenario-toggle"></span>\s*'
    r'</summary>\s*'
    r'<div class="extreme-scenario-body">\s*'
    r'(?:<div class="extreme-scenario-content"[^>]*>)?\s*',
    re.DOTALL
)

# details 블록 끝
DETAILS_END = re.compile(
    r'\s*(?:</div>\s*)?</div>\s*</details>\s*',
    re.DOTALL
)

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'extreme-scenario-details' not in content:
        return False

    # 시작 부분을 ## 극한 시나리오 헤더로 교체
    content = DETAILS_START.sub('\n## 극한 시나리오\n\n', content)

    # 끝 부분 제거
    content = DETAILS_END.sub('\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

files = glob.glob(os.path.join(POSTS_DIR, "**", "*.md"), recursive=True)
count = 0
for f in files:
    if process_file(f):
        count += 1

print(f"Done: {count} files reverted")
