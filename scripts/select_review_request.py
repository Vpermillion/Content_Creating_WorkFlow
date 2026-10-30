"""Select one committed review request for the bounded GitHub production job."""
import json
from pathlib import Path
import re
import subprocess


def select_request(names, root):
    selected = [n for n in names if n.startswith('review-requests/') and n.endswith('.json')]
    if len(selected) != 1:
        raise ValueError('Commit exactly one review request')
    name = selected[0]
    if not re.fullmatch(r'review-requests/[a-z0-9][a-z0-9-]{0,99}\.json', name):
        raise ValueError('Invalid request path')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve() / 'review-requests') or path.stat().st_size > 100_000:
        raise ValueError('Invalid request file')
    data = json.loads(path.read_text())
    ident = data.get('id', '')
    if data.get('schema_version') != 1 or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', ident):
        raise ValueError('Invalid review request identity')
    if data.get('result_branch') != 'codex/results/' + ident:
        raise ValueError('Results must use the request-specific result branch')
    return name, ident


if __name__ == '__main__':
    import os
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'],
                                    cwd=root, text=True).splitlines()
    name, ident = select_request(names, root)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('path=' + name + '\n')
        output.write('id=' + ident + '\n')
    print(json.dumps({'request': name, 'id': ident}))
