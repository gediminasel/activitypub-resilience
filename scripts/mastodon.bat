git diff --stat=10000 211958e | python -c "import sys;[print(r.split('|')[0]) for r in sys.stdin.readlines()]"
git diff --shortstat 211958e | python -c "print(int(input().split('changed,')[-1].split('insertions')[0]))"