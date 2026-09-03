# -*- coding: utf-8 -*-
# Diagnostico: por que o Responsavel (do Cadastro) nao aparece no filtro da aba Demanda
import os, sqlite3, re

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")
APP = os.path.join(BASE, "app.py")
DB = os.path.join(BASE, "sistema.db")

print("############ 1) FILTRO RESPONSAVEL NA FICHA (ficha_pessoa.html) ############")
with open(FICHA, "r", encoding="utf-8") as f:
    linhas = f.readlines()
for i, l in enumerate(linhas):
    if "responsavel" in l.lower():
        a = max(0, i-3); b = min(len(linhas), i+6)
        print("\n--- linha %d ---" % (i+1))
        for j in range(a, b):
            print("%4d: %s" % (j+1, linhas[j].rstrip()[:220]))

print("\n\n############ 2) RESPONSAVEL NO app.py (rotas que rendem a ficha/demanda) ############")
with open(APP, "r", encoding="utf-8") as f:
    app_txt = f.read()
for i, l in enumerate(app_txt.splitlines(), 1):
    if "responsavel" in l.lower():
        a = max(0, i-4); b = min(len(app_txt.splitlines()), i+8)
        print("\n--- app.py linha %d ---" % i)
        for j in range(a, b):
            print("%4d: %s" % (j+1, app_txt.splitlines()[j-1][:220]))

print("\n\n############ 3) BANCO: pessoas cadastradas e colunas da tabela demanda ############")
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    n = cur.execute("SELECT COUNT(*) FROM pessoas").fetchone()[0]
    print("Pessoas cadastradas:", n)
    if n > 0:
        rows = cur.execute("SELECT id, nome FROM pessoas ORDER BY nome LIMIT 15").fetchall()
        for r in rows:
            print("  id=%s | %s" % (r[0], r[1]))
except Exception as e:
    print("Erro ao listar pessoas:", e)
try:
    cols = [r[1] for r in cur.execute("PRAGMA table_info(demandas)")]
    print("\nColunas da tabela 'demandas':", ", ".join(cols))
except Exception as e:
    try:
        cols = [r[1] for r in cur.execute("PRAGMA table_info(demanda)")]
        print("\nColunas da tabela 'demanda':", ", ".join(cols))
    except Exception as e2:
        print("Nao achei tabela demandas/demanda:", e2)
conn.close()