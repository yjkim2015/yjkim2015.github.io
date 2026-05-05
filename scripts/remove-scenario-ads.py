"""극한 시나리오 details 안의 광고 블록과 ontoggle 속성 제거"""
import glob, os, re

POSTS_DIR = r"C:\Users\Kim\OneDrive\문서\yjkim2015.github.io\_posts"

AD_BLOCK = """<div class="extreme-scenario-ad" style="text-align:center; margin-bottom:1.5em;">
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-7225106491387870"
     data-ad-slot="0000000000"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
</div>"""

ONTOGGLE = ' ontoggle="if(this.open){var ad=this.querySelector(\'.extreme-scenario-ad\');if(ad&&!ad.dataset.loaded){ad.dataset.loaded=\'1\';(adsbygoogle=window.adsbygoogle||[]).push({});}}"'

files = glob.glob(os.path.join(POSTS_DIR, "**", "*.md"), recursive=True)
count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content
    content = content.replace(AD_BLOCK, '')
    content = content.replace(ONTOGGLE, '')
    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        count += 1
        print(f"  [OK] {os.path.relpath(f, POSTS_DIR)}")

print(f"\nDone: {count} files cleaned")
