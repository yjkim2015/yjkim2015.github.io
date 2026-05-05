"""
극한 시나리오 섹션을 <details> 접기/펼치기로 변환하는 스크립트.
극한 시나리오 헤더(## 극한 시나리오 또는 ## N. 극한 시나리오)를 찾아서
다음 같은 레벨 헤더까지의 콘텐츠를 details 블록으로 감싼다.
"""
import re
import glob
import os

POSTS_DIR = r"C:\Users\Kim\OneDrive\문서\yjkim2015.github.io\_posts"

# 극한 시나리오 헤더 패턴
EXTREME_HEADER = re.compile(
    r'^(#{2})\s+(?:\d+[\.\-]\s*)?극한\s*시나리오.*$',
    re.MULTILINE
)

DETAILS_OPEN = """<details class="extreme-scenario-details" ontoggle="if(this.open){var ad=this.querySelector('.extreme-scenario-ad');if(ad&&!ad.dataset.loaded){ad.dataset.loaded='1';(adsbygoogle=window.adsbygoogle||[]).push({});}}">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">
<div class="extreme-scenario-ad" style="text-align:center; margin-bottom:1.5em;">
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-7225106491387870"
     data-ad-slot="0000000000"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
</div>
<div class="extreme-scenario-content" markdown="1">
"""

DETAILS_CLOSE = """</div>
</div>
</details>
"""

def find_next_h2(content, start_pos):
    """start_pos 이후의 다음 ## 헤더 위치를 찾는다."""
    pattern = re.compile(r'^## ', re.MULTILINE)
    match = pattern.search(content, start_pos)
    if match:
        return match.start()
    return len(content)

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 이미 변환된 파일은 건너뛰기
    if 'extreme-scenario-details' in content:
        return False

    match = EXTREME_HEADER.search(content)
    if not match:
        return False

    header_start = match.start()
    header_end = match.end()

    # 헤더 다음 줄부터 시작
    content_start = header_end + 1

    # 다음 같은 레벨(##) 헤더 또는 --- 구분선 찾기
    next_section = find_next_h2(content, content_start)

    # 극한 시나리오 콘텐츠 추출
    scenario_content = content[content_start:next_section].rstrip()

    # 조립
    new_content = (
        content[:header_start] +
        DETAILS_OPEN +
        scenario_content + "\n" +
        DETAILS_CLOSE + "\n" +
        content[next_section:]
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True

def main():
    files = glob.glob(os.path.join(POSTS_DIR, "**", "*.md"), recursive=True)
    converted = 0
    skipped = 0
    errors = []

    for f in sorted(files):
        try:
            if process_file(f):
                converted += 1
                rel = os.path.relpath(f, POSTS_DIR)
                print(f"  [OK] {rel}")
            else:
                skipped += 1
        except Exception as e:
            errors.append((f, str(e)))
            print(f"  [FAIL] {os.path.relpath(f, POSTS_DIR)}: {e}")

    print(f"\n완료: {converted}개 변환, {skipped}개 건너뜀, {len(errors)}개 오류")

if __name__ == "__main__":
    main()
