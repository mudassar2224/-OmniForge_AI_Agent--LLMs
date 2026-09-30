import pathlib
import os

path = pathlib.Path('src/omniforge/config/models.py')
text = path.read_text('utf-8')

import re
text = re.sub(
    r'if not self\.settings\.GEMINI_API_KEY:\s*return \[\]\s*llm = ChatGoogleGenerativeAI\(\s*api_key=self\.settings\.GEMINI_API_KEY,',
    r'gemini_key = __import__("os").environ.get("GEMINI_API_KEY")\n        if not gemini_key:\n            return []\n        llm = ChatGoogleGenerativeAI(\n            api_key=gemini_key,',
    text
)

path.write_text(text, 'utf-8')
print("Patched models.py successfully.")
