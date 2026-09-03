# -*- coding: utf-8 -*-
# Botao "Gerar Etiqueta" da ABA KIT agora abre a pagina Kit/Envio de Material - Etiquetas direto para a pessoa.
import os, re, sys, time, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")

def ler(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()
def gravar(p, txt):
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)

# ---------- 0) BACKUP ----------
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(APP, APP + ".bak_" + ts)
if os.path.exists(FICHA):
    shutil.copy(FICHA, FICHA + ".bak_" + ts)
print("[0/3] Backup criado: *.bak_" + ts)

# ---------- 1) ROTA no app.py ----------
app_txt = ler(APP)
if "kit_etiqueta" in app_txt:
    print("[1/3] Rota 'kit_etiqueta' ja existe. Pulando.")
else:
    ROTA = '''

# ===== ROTA: GERAR ETIQUETA DA ABA KIT (etiqueta de envio direto para a pessoa) =====
@app.route("/pessoas/<int:pid>/imprimir/kit_etiqueta")
@login_obrigatorio
def pessoa_imprimir_kit_etiqueta(pid):
    p = buscar("SELECT * FROM pessoas WHERE id=%s", (pid,))
    if not p:
        flash("Registro nao encontrado.", "erro")
        return redirect(url_for("pessoas"))
    try:
        _impr_garante_colunas()
    except Exception:
        pass
    mapa = _impr_mapa_pessoas()
    etqs = _impr_etqs_pessoas([str(pid)], mapa)
    cand = candidato_ativo() or {}
    conteudo = sane(request.args.get("conteudo") or "Material de campanha")
    quantidade = sane(request.args.get("quantidade") or "1")
    peso = sane(request.args.get("peso") or "")
    valor = sane(request.args.get("valor") or "")
    seq_val = sane(request.args.get("seq") or "1")
    try:
        seq_atual = int(seq_val) or 1
    except Exception:
        seq_atual = 1
    modelo = sane(request.args.get("modelo") or "correios")
    if modelo not in ("correios", "transportadora"):
        modelo = "correios"
    sigla_base = cand.get("nome_urna") or "CARLISE"
    sigla = "".join(ch for ch in str(sigla_base).upper() if ch.isalnum())[:6] or "C2233"
    for e in etqs:
        codigo = "%s-%04d-%03d" % (sigla, int(e["id"] or 0), seq_atual)
        e["codigo"] = codigo
        e["barra"] = _impr_code39_svg(codigo)
        e["num_envio"] = seq_atual
        e["conteudo"] = conteudo
        e["quantidade"] = quantidade
        e["peso"] = peso
        e["valor"] = valor
        e["modelo"] = modelo
        seq_atual += 1
    from datetime import datetime as _dth
    return render_template("impressao_etiquetas_kits.html", cand=cand,
                           etiquetas=etqs, data_hoje=_dth.now().strftime("%d/%m/%Y"))
'''
    alvo = app_txt.rfind("if __name__")
    if alvo == -1:
        alvo = app_txt.rfind("app.run(")
    if alvo == -1:
        print("[!] Nao achei ponto de insercao. Nada gravado.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTA + "\n\n" + app_txt[alvo:]
    gravar(APP, app_txt)
    print("[1/3] Rota de geracao da etiqueta (Kit) adicionada ao app.py.")

# ---------- 2) BOTAO na ficha (aba Kit -> LISTA DE SELECAO) ----------
if os.path.exists(FICHA):
    ficha = ler(FICHA)
    antigo = '<button class="btn btn-p" type="button" onclick="window.print()">Gerar Etiqueta</button>'
    novo = '<a class="btn btn-p" href="/pessoas/{{ p.id }}/imprimir/kit_etiqueta">Gerar Etiqueta</a>'
    if antigo in ficha:
        ficha = ficha.replace(antigo, novo)
        gravar(FICHA, ficha)
        print("[2/3] Botao 'Gerar Etiqueta' agora abre a etiqueta de envio direto da pessoa.")
    else:
        padrao = re.compile(r'<button[^>]*class="btn btn-p"[^>]*onclick="window\.print\(\)"[^>]*>\s*Gerar Etiqueta\s*</button>')
        ficha2, n = padrao.subn(novo, ficha)
        if n:
            gravar(FICHA, ficha2)
            print("[2/3] Botao 'Gerar Etiqueta' atualizado (via regex).")
        else:
            print("[2/3] AVISO: nao encontrei o botao 'Gerar Etiqueta' na ficha - nada alterado.")
else:
    print("[2/3] ficha_pessoa.html nao encontrado - nao alterei.")

# ---------- 3) VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor e teste: ficha da pessoa -> aba Kit -> Gerar Etiqueta.")