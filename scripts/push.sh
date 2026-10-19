#!/usr/bin/env bash
# Push main after a commit (John 19/10: the cinema page is pushed as we go, without a prompt each time; the global
# "ask: git push" rule stays for every other repo). Rebases on the remote first, like finals.sh's publish pass.
set -eu
cd "$(dirname "$0")/.."
git pull -q --rebase --autostash
git push -q
git log --oneline -1
