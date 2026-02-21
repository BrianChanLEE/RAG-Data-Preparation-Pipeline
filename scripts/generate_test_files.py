import fitz
import zipfile
import os

os.makedirs("data/raw", exist_ok=True)

# 1. Create a valid PDF
doc = fitz.open()
page = doc.new_page()
# write enough text to pass the min_chars check (default 300)
# write enough text to pass the min_chars check (default 300)
# Use larger font for headings
page.insert_text((50, 50), "Chapter 1", fontsize=16)

text_lines = []
text_lines.extend([f"This is line {i}. It represents a full sentence ending with punctuation! Then another sentence." for i in range(15)])
page.insert_text((50, 70), "\n".join(text_lines), fontsize=11)

page.insert_text((50, 400), "Chapter 2", fontsize=16)
text_lines = []
text_lines.extend([f"Here is chapter two, line {i}. Did you know that sentence chunking works? Yes, it does." for i in range(15)])
page.insert_text((50, 420), "\n".join(text_lines), fontsize=11)
doc.save("data/raw/valid.pdf")
doc.close()

# 2. Create a valid JWPUB
os.makedirs("temp_jwpub/contents", exist_ok=True)
html_content = """<html>
<body>
<h1>제 1 장 제목</h1>
<p>""" + "이것은 JWPUB 테스트 내용입니다. " * 30 + """</p>
</body>
</html>"""
with open("temp_jwpub/contents/1.html", "w", encoding="utf-8") as f:
    f.write(html_content)

with zipfile.ZipFile("data/raw/valid.jwpub", "w") as zf:
    zf.write("temp_jwpub/contents/1.html", arcname="contents/1.html")

# 3. Create an invalid file
with open("data/raw/invalid.txt", "w") as f:
    f.write("이것은 지원하지 않는 파일입니다.")
