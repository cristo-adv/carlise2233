# -*- coding: utf-8 -*-
# Adiciona a rota /api/pessoas_opcoes (lista de pessoas para o select Responsavel do Cadastro) no app.py
import os, re, time, shutil, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")

def ler(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()
def gravar(p, txt):
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)

# ---------- 0) BACKUP ----------
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(APP, APP + ".bak_" + ts)
print("[0/3] Backup: app.py.bak_" + ts)

app_txt = ler(APP)

# ---------- 1) GARANTE o import de jsonify ----------
m = re.search(r"from flask import ([^\n]+)", app_txt)
if not m:
    print("[!] Nao achei o import do flask. Abortando para nao quebrar.")
    raise SystemExit
imports = m.group(1)
if "jsonify" not in imports:
    novo_imports = imports.strip()
    if novo_imports.endswith(")"):
        novo_imports = novo_imports.rstrip()[:-1] + ", jsonify)"
    else:
        novo_imports = novo_imports + ", jsonify"
    app_txt = app_txt[:m.start(1)] + novo_imports + app_txt[m.end(1):]
    print("[1/3] Import de 'jsonify' adicionado ao Flask.")
else:
    print("[1/3] 'jsonify' ja importado. Pulando.")

# ---------- 2) CRIA a rota /api/pessoas_opcoes se nao existir ----------
if "pessoas_opcoes" in app_txt:
    print("[2/3] AVISO: a rota /api/pessoas_opcoes JA existe no app.py. Vou mostrar o trecho para conferir:")
    i = app_txt.find("pessoas_opcoes")
    print(app_txt[max(0, i-200):i+800])
else:
    ROTA = '''

@app.route("/api/pessoas_opcoes")
@login_obrigatorio
def api_pessoas_opcoes():
    """Lista as pessoas para o select 'Responsavel (do Cadastro)' nas abas Demanda, Autorizacao e Contrato."""
    tipo = (sane(request.args.get("tipo") or "") or "").upper().strip()
    try:
        linhas = listar("SELECT id, nome, tipo, funcao FROM pessoas ORDER BY nome COLLATE NOCASE")
    except Exception:
        linhas = []
    out = []
    for r in linhas:
        nome = str(r.get("nome") or "").strip()
        if not nome:
            continue
        tp = str(r.get("tipo") or "").upper()
        fn = str(r.get("funcao") or "").upper()
        if tipo and tipo not in tp and tipo not in fn:
            continue
        out.append({"id": r.get("id"), "nome": nome})
    return jsonify(out)
'''
    alvo = app_txt.rfind("if __name__")
    if alvo == -1:
        alvo = app_txt.rfind("app.run(")
    if alvo == -1:
        print("[!] Nao achei ponto de insercao. Nada gravado.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTA + "\n\n" + app_txt[alvo:]
    gravar(APP, app_txt)
    print("[2/3] Rota /api/pessoas_opcoes criada (lista as pessoas cadastradas).")

# ---------- 3) VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor e abra a ficha de uma pessoa -> aba Demandas.")