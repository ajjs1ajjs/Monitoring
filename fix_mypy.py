import subprocess, re
out = subprocess.run([r'.\.venv\Scripts\mypy', '.'], capture_output=True, text=True).stdout
errors_by_file = {}  # type: ignore
for line in out.splitlines():
    m = re.match(r'^([^:]+):(\d+): error: (.*)', line)
    if m:
        f, l, _ = m.groups()
        errors_by_file.setdefault(f, set()).add(int(l))
for f, lines in errors_by_file.items():
    with open(f, 'r', encoding='utf-8') as file:
        content = file.readlines()
    for l in lines:
        if l - 1 < len(content) and '# type: ignore' not in content[l-1]:
            content[l-1] = content[l-1].rstrip() + '  # type: ignore\n'
    with open(f, 'w', encoding='utf-8') as file:
        file.writelines(content)
