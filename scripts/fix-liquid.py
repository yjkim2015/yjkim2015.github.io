"""
코드블록 안의 {{ }} 를 Jekyll이 처리하지 않도록
코드블록을 {% raw %}...{% endraw %}로 감싼다.
이미 raw로 감싸진 블록은 건너뛴다.
"""
import re, glob, os

POSTS_DIR = r"C:\Users\Kim\OneDrive\문서\yjkim2015.github.io\_posts"

# 코드블록 패턴 (``` ... ```)
CODE_BLOCK = re.compile(r'(```[^\n]*\n)(.*?)(```)', re.DOTALL)

def needs_raw(code_content):
    """코드 안에 {{ 또는 {% 가 있는지"""
    return '{{' in code_content or '{%' in code_content

def wrap_raw(match):
    opener = match.group(1)  # ```yaml\n
    content = match.group(2)
    closer = match.group(3)  # ```

    if not needs_raw(content):
        return match.group(0)

    # 이미 raw로 감싸져 있으면 건너뛰기
    if '{% raw %}' in content or '{% endraw %}' in content:
        return match.group(0)

    return '{% raw %}\n' + opener + content + closer + '\n{% endraw %}'

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = CODE_BLOCK.sub(wrap_raw, content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

files = glob.glob(os.path.join(POSTS_DIR, "**", "*.md"), recursive=True)
count = 0
for f in sorted(files):
    if process_file(f):
        count += 1
        print(f"  [OK] {os.path.relpath(f, POSTS_DIR)}")

print(f"\nDone: {count} files fixed")
