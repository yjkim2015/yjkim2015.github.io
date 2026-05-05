"""
details 태그가 kramdown에 의해 제거되는 문제 수정.
방법: details 블록 전체를 {::nomarkdown}...{:/nomarkdown} 로 감싸서
kramdown이 건드리지 못하게 한다. 단, 내부 마크다운은 렌더링되지 않으므로
summary만 HTML로 두고, 내부 콘텐츠는 마크다운 그대로 둔다.

최종 접근: details/summary는 유지하되 markdown="1"을 제거하고
details 안의 마크다운이 자연스럽게 렌더링되도록 한다.
kramdown에서 HTML 블록 뒤에 빈 줄이 있으면 마크다운으로 처리한다.
"""
import glob, os, re

POSTS_DIR = r"C:\Users\Kim\OneDrive\문서\yjkim2015.github.io\_posts"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'extreme-scenario-details' not in content:
        return False

    original = content

    # markdown="1" 제거
    content = content.replace(' markdown="1"', '')

    # <div class="extreme-scenario-body"> 뒤에 빈 줄 보장
    content = content.replace(
        '<div class="extreme-scenario-body">\n\n<div class="extreme-scenario-content">',
        '<div class="extreme-scenario-body">\n<div class="extreme-scenario-content">\n'
    )
    content = content.replace(
        '<div class="extreme-scenario-body">\n<div class="extreme-scenario-content">\n',
        '<div class="extreme-scenario-body">\n<div class="extreme-scenario-content" markdown="1">\n\n'
    )

    if content == original:
        return False

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

files = glob.glob(os.path.join(POSTS_DIR, "**", "*.md"), recursive=True)
count = 0
for f in files:
    if process_file(f):
        count += 1

print(f"Done: {count} files fixed")
