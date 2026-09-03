# -*- coding: utf-8 -*-
# Diagnostico focado: porque o Responsavel (do Cadastro) nao aparece no select da aba Demanda
import os, json, sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")
DB = os.path.join(BASE, "sistema.db")

print("############ A) JS E HTML QUE POPULAM O RESPONSAVEL (ficha_pessoa.html) ############")
with open(FICHA, encoding="utf-8") as f:
    linhas = f.readlines()

chaves = ["pessoas_opcoes", "selResp", "CARREGANDO", "Responsavel", "responsavel"]
marcadas = set()
for i, l in enumerate(linhas):
    if any(k.lower() in l.lower() for k in chaves):
        marcadas.add(i)

grupos = []
for i in sorted(marcadas):
    if grupos and i - grupos[-1][-1] <= 3:
        grupos[-1].append(i)
    else:
        grupos.append([i])

if not grupos:
    print("(nenhuma linha com essas palavras encontrada)")
for g in grupos[:8]:
    a = max(0, g[0]-3)
    b = min(len(linhas), g[-1]+10)
    print("\n---- bloco linhas %d..%d ----" % (a+1, b))
    for j in range(a, b):
        print("%4d: %s" % (j+1, linhas[j].rstrip()[:230]))

print("\n\n############ B) RESPOSTA DA API /api/pessoas_opcoes (simulada com o mesmo SQL) ############")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
try:
    total = conn.execute("SELECT COUNT(*) FROM pessoas").fetchone()[0]
    print("Total de pessoas na base:", total)
    rows = conn.execute("SELECT id, nome, tipo, funcao, municipio FROM pessoas ORDER BY nome LIMIT 5").fetchall()
    amostra = [{"id": r["id"], "nome": r["nome"], "tipo": r["tipo"], "funcao": r["funcao"], "municipio": r["municipio"]} for r in rows]
    print("Exemplo do que a API entrega (primeiras 5):")
    print(json.dumps(amostra, ensure_ascii=False, indent=2))
except Exception as e:
    print("Erro ao simular:", e)
conn.close()

print("\n\n############ C) COLUNAS DA TABELA DE DEMANDAS ############")
conn = sqlite3.connect(DB)
try:
    for t in ("demandas", "demanda"):
        cols = [r[1] for r in conn.execute("PRAGMA table_info(" + t + ")")]
        if cols:
            print("Tabela %s: %s" % (t, ", ".join(cols)))
except Exception as e:
    print("Erro:", e)
conn.close()