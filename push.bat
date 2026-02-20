@echo off
git add .
git commit -m "docs: add uninstall guide to multi-language READMEs"
git push origin main > push_result.txt 2>&1
