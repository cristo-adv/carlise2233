# -*- coding: utf-8 -*-
# Limpa o repositorio git: remove __pycache__ e backups .bak_* do controle de versao
import os, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

def run(*args):
    return subprocess.run(args, cwd=BASE, capture_output=True, text=True)

# garante o .gitignore
gitignore = """__pycache__/
*.pyc
*.pyo
.env
venv/
*.bak
*.bak_*
"""
with open(os.path.join(BASE, ".gitignore"), "w", encoding="utf-8") as f:
    f.write(gitignore)
print("[1/3] .gitignore garantido.")

# remove do indice (mantendo os arquivos no disco)
for alvo in ("__pycache__", "*.pyc", "*.bak_*"):
    r = run("git", "rm", "-r", "--cached", "--ignore-unmatch", alvo)
    print("[2/3] git rm --cached", alvo, "->", "ok" if r.returncode == 0 else "sem itens")

# commit da limpeza
r = run("git", "add", ".")
run("git", "commit", "-m", "limpeza: remove pycache e backups do controle de versao")
print("[3/3] Commit de limpeza feito.")

r = run("git", "status", "--short")
print("\nStatus atual (deve estar limpo ou so com o .gitignore):")
print(r.stdout or "(vazio)")