@echo off
echo src
pygount --format=summary src --folders-to-skip=out,res,.idea,__pycache__,.pytest_cache,.vscode --names-to-skip=*.db,*.ini,*.exe
echo tests
pygount --format=summary tests --folders-to-skip=out,res,.idea,__pycache__,.pytest_cache,.vscode --names-to-skip=*.db,*.ini,*.exe
echo other
pygount --format=summary  . --folders-to-skip=out,res,.idea,__pycache__,.pytest_cache,res,tests,src,.vscode --names-to-skip=*.db,*.ini,*.exe,*.md,*.o,.depend,LICENSE