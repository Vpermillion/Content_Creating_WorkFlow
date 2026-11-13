"""Save a bounded CI result on a dedicated ref, without test logs or secrets."""
import json
import os
import subprocess


def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data).decode().strip()


def main():
    ref = 'refs/heads/codex/ci/ifverse-chatgpt-publishing'
    result = {'commit': os.environ['GITHUB_SHA'], 'conclusion': os.environ['CI_RESULT'],
              'python': os.environ['PYTHON_RESULT'], 'mcp': os.environ['MCP_RESULT'],
              'run_id': os.environ['GITHUB_RUN_ID'],
              'run_url': 'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']}
    blob = git('hash-object', '-w', '--stdin', data=json.dumps(result, indent=2).encode())
    tree = git('mktree', data=f'100644 blob {blob}\tresult.json\n'.encode())
    parent = []
    if git('ls-remote', 'origin', ref):
        git('fetch', '--quiet', 'origin', ref)
        parent = ['-p', git('rev-parse', 'FETCH_HEAD')]
    commit = git('-c', 'user.name=github-actions[bot]', '-c',
        'user.email=41898282+github-actions[bot]@users.noreply.github.com',
        'commit-tree', tree, *parent, '-m', 'Record Ifverse publishing software CI result')
    git('push', '--quiet', 'origin', commit + ':' + ref)


if __name__ == '__main__':
    main()
