import sys
sys.path.insert(0, 'src')
from omniforge.agents import _extract_code_blocks
from omniforge.coding.verifier import verify_python_syntax

text1 = """Here is the code:
```python
import os
print("Hello")
```
"""

text2 = """```python
import os
print("Hello")
```"""

print("Test 1:", _extract_code_blocks(text1))
print("Test 2:", _extract_code_blocks(text2))

# What if line startswith ``` but has spaces?
text3 = """
 ```python
import os
 ```
"""
print("Test 3:", _extract_code_blocks(text3))
