import os
import re

roots = [r"C:\Users\aa22s\.gemini\antigravity\brain"]
# classic token ghp_[a-zA-Z0-9]{36} or github_pat_[a-zA-Z0-9_]{82} or 40 hex chars
patterns = [
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'github_pat_[a-zA-Z0-9_]{82}'),
    re.compile(r'\b[0-9a-fA-F]{40}\b')
]

found = False
for root_dir in roots:
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for p in patterns:
                        matches = p.findall(content)
                        if matches:
                            print(f"FOUND in {path}: {matches}")
                            found = True
            except Exception:
                pass

if not found:
    print("NO PAT FOUND")
