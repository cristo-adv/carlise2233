# -*- coding: utf-8 -*-
# Adiciona a aba IMPRESSAO dentro da ficha da pessoa no CARLISE-2233 (visao geral, contratos, oficios, recibo eleitoral).
import os, sqlite3, sys, re, time, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")
DB = os.path.join(BASE, "sistema.db")
TPL = os.path.join(BASE, "templates")

def ler(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def gravar(p, txt):
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)

# ---------- 0) BACKUP ----------
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(APP, APP + ".bak_" + ts)
ficha_p = os.path.join(TPL, "ficha_pessoa.html")
if os.path.exists(ficha_p):
    shutil.copy(ficha_p, ficha_p + ".bak_" + ts)
print("[0/5] Backup criado: *.bak_" + ts)

# ---------- 1) ROTAS DE IMPRESSAO DA FICHA ----------
app_txt = ler(APP)
if "/pessoas/<int:pid>/imprimir" in app_txt:
    print("[1/5] Rotas de impressao da ficha ja existem. Pulando.")
else:
    ROTAS = '''

# ===== ABA IMPRESSAO NA FICHA DA PESSOA (visao geral, contratos, oficios, recibo eleitoral) =====
import sqlite3 as _ipp_sq
import os as _ipp_os
from datetime import datetime as _ipp_dt

_IPP_BD = _ipp_os.path.join(_ipp_os.path.dirname(_ipp_os.path.abspath(__file__)), "sistema.db")

def _ipp_conn():
    conn = _ipp_sq.connect(_IPP_BD)
    conn.row_factory = _ipp_sq.Row
    return conn

def _ipp_colunas(tabela):
    try:
        conn = _ipp_conn()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(" + tabela + ")")]
        conn.close()
        return cols
    except Exception:
        return []

def _ipp_tem(tabela):
    try:
        conn = _ipp_conn()
        n = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone()[0]
        conn.close()
        return n > 0
    except Exception:
        return False

def _ipp_linhas(sql, params=()):
    try:
        conn = _ipp_conn()
        conn.row_factory = _ipp_sq.Row
        rows = [dict(r) for r in conn.execute(sql, params)]
        conn.close()
        return rows
    except Exception:
        return []

@app.route("/pessoas/<int:pid>/imprimir")
@login_obrigatorio
def pessoa_imprimir(pid):
    p = buscar("SELECT * FROM pessoas WHERE id=%s", (pid,))
    if not p:
        flash("Registro nao encontrado.", "erro")
        return redirect(url_for("pessoas"))
    colunas = _ipp_colunas("pessoas")
    return render_template("pessoa_imprimir.html", p=p, cand=candidato_ativo(), colunas=colunas)

@app.route("/pessoas/<int:pid>/imprimir/contratos")
@login_obrigatorio
def pessoa_imprimir_contratos(pid):
    p = buscar("SELECT * FROM pessoas WHERE id=%s", (pid,))
    if not p:
        flash("Registro nao encontrado.", "erro")
        return redirect(url_for("pessoas"))
    contratos = _ipp_linhas("SELECT * FROM contratos WHERE pessoa_id=%s ORDER BY id DESC", (pid,)) if _ipp_tem("contratos") else []
    return render_template("pessoa_imprimir_contratos.html", p=p, cand=candidato_ativo(), contratos=contratos)

@app.route("/pessoas/<int:pid>/imprimir/oficios")
@login_obrigatorio
def pessoa_imprimir_oficios(pid):
    p = buscar("SELECT * FROM pessoas WHERE id=%s", (pid,))
    if not p:
        flash("Registro nao encontrado.", "erro")
        return redirect(url_for("pessoas"))
    oficios = _ipp_linhas("SELECT * FROM oficios WHERE pessoa_id=%s ORDER BY id DESC", (pid,)) if _ipp_tem("oficios") else []
    return render_template("pessoa_imprimir_oficios.html", p=p, cand=candidato_ativo(), oficios=oficios)

@app.route("/pessoas/<int:pid>/imprimir/recibo")
@login_obrigatorio
def pessoa_imprimir_recibo(pid):
    p = buscar("SELECT * FROM pessoas WHERE id=%s", (pid,))
    if not p:
        flash("Registro nao encontrado.", "erro")
        return redirect(url_for("pessoas"))
    materiais = []
    if _ipp_tem("kits"):
        kits = _ipp_linhas("SELECT * FROM kits WHERE pessoa_id=%s ORDER BY id DESC", (pid,))
        for k in kits:
            itens = _ipp_linhas("SELECT * FROM kit_itens WHERE kit_id=%s ORDER BY id", (k["id"],))
            for it in itens:
                materiais.append({"material": it.get("material") or "", "quantidade": it.get("quantidade") or "", "kit": k.get("nome") or ""})
    return render_template("pessoa_imprimir_recibo.html", p=p, cand=candidato_ativo(),
                           materiais=materiais, data_hoje=_ipp_dt.now().strftime("%d/%m/%Y"))
'''
    alvo = app_txt.find("if __name__")
    if alvo == -1:
        alvo = app_txt.find("app.run(")
    if alvo == -1:
        print("[!] Nao achei ponto de insercao. Nada gravado.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTAS + "\n\n" + app_txt[alvo:]
    gravar(APP, app_txt)
    print("[1/5] Rotas de impressao da ficha adicionadas ao app.py.")

# ---------- 2) ABA IMPRESSAO NA FICHA ----------
if os.path.exists(ficha_p):
    ficha = ler(ficha_p)
    if "aba-impressao" in ficha:
        print("[2/5] Aba Impressao ja existe na ficha. Pulando insercao.")
    else:
        # 2a) remove o trecho que causava erro 'pessoa' undefined (se ainda existir)
        for a in ["or pessoa.data_aniversario", "or pessoa.categoria", "or pessoa.demandas", "or pessoa.observacao"]:
            ficha = ficha.replace(a, "")

        # 2b) adiciona o link da aba "Impressao" junto das outras abas
        def inserir_aba(ficha):
            alvos = ["Contratos", "Ve\u00edculos", "Veiculos", "Cadastro", "Kit"]
            for alvo in alvos:
                m = re.search(r"<a\b[^>]*>\s*" + re.escape(alvo) + r"\s*</a>", ficha, re.I)
                if m:
                    elem = m.group(0)
                    if "aba=" in elem:
                        novo = re.sub(r"(aba=)[^\"'&\s]*", r"\1impressao", elem)
                    else:
                        novo = re.sub(r'(href=")[^"]*(")', r"\1?aba=impressao\2", elem)
                    novo = re.sub(r">\s*" + re.escape(alvo) + r"\s*<", ">Impress\u00e3o<", novo, flags=re.I)
                    return ficha[:m.end()] + novo + ficha[m.end():], True
            return ficha, False

        ficha, ok = inserir_aba(ficha)
        if ok:
            print("[2/5] Link da aba 'Impress\u00e3o' adicionado junto das outras abas.")
        else:
            i = ficha.find("{% if aba")
            if i != -1:
                ficha = ficha[:i] + '<a href="?aba=impressao">Impress\u00e3o</a>\n' + ficha[i:]
                print("[2/5] Aviso: inseri o link 'Impress\u00e3o' acima do conteudo das abas (nao achei as abas existentes).")
            else:
                print("[2/5] Aviso: nao consegui inserir o link da aba - o conteudo ainda aparecera com ?aba=impressao.")

        # 2c) conteudo da aba Impressao (cards de impressao)
        bloco = '''

{% if aba == 'impressao' %}
<div class="aba-impressao" style="padding:16px;border:1px solid #ddd;border-radius:10px;margin-top:14px">
  <h3 style="margin:0 0 4px 0">Impress\u00e3o do cadastro</h3>
  <p style="color:#666;font-size:13px;margin:0 0 14px 0">Escolha o que deseja imprimir desta pessoa. As p\u00e1ginas abrem em formato de impress\u00e3o direta.</p>
  {% if p %}
  <div style="display:flex;flex-wrap:wrap;gap:12px">
    <a href="/pessoas/{{ p.id }}/imprimir" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
      <div style="font-size:20px">\U0001F5A8\U0000FE0F</div>
      <strong style="color:#0050FF">Vis\u00e3o geral do cadastro</strong>
      <div style="font-size:12px;color:#666;margin-top:4px">Ficha completa da pessoa, todos os campos, pronta para imprimir</div>
    </a>
    <a href="/pessoas/{{ p.id }}/imprimir/contratos" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
      <div style="font-size:20px">\U0001F4C4</div>
      <strong style="color:#0050FF">Contratos</strong>
      <div style="font-size:12px;color:#666;margin-top:4px">Imprime os contratos registrados desta pessoa</div>
    </a>
    <a href="/pessoas/{{ p.id }}/imprimir/oficios" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
      <div style="font-size:20px">\u2709\uFE0F</div>
      <strong style="color:#0050FF">Of\u00edcios</strong>
      <div style="font-size:12px;color:#666;margin-top:4px">Imprime os of\u00edcios relacionados a esta pessoa</div>
    </a>
    <a href="/pessoas/{{ p.id }}/imprimir/recibo" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
      <div style="font-size:20px">\U0001F4CB</div>
      <strong style="color:#0050FF">Recibo eleitoral</strong>
      <div style="font-size:12px;color:#666;margin-top:4px">Recibo de entrega de material de campanha, conforme a legisla\u00e7\u00e3o eleitoral</div>
    </a>
  </div>
  {% else %}
  <p style="color:#888">Salve o cadastro primeiro para liberar as impress\u00f5es desta pessoa.</p>
  {% endif %}
</div>
{% endif %}

'''
        iend = ficha.rfind("{% endblock %}")
        if iend != -1:
            ficha = ficha[:iend] + bloco + "\n" + ficha[iend:]
            gravar(ficha_p, ficha)
            print("[2/5] Conteudo da aba Impressao inserido na ficha.")
        else:
            print("[2/5] Aviso: nao achei {% endblock %} - conteudo nao inserido.")
else:
    print("[2/5] ficha_pessoa.html nao encontrado - pulei.")

# ---------- 3) TEMPLATES DE IMPRESSAO ----------
os.makedirs(TPL, exist_ok=True)

gravar(os.path.join(TPL, "pessoa_imprimir.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Vis\u00e3o geral do cadastro</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; color: #000; }
  .no-print { margin-bottom: 10px; }
  .cab { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 14px; }
  .cab .l1 { font-size: 18px; font-weight: bold; }
  .cab .l2 { font-size: 13px; }
  h2 { text-align: center; font-size: 18px; margin: 8px 0; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { border: 1px solid #333; padding: 5px; text-align: left; vertical-align: top; }
  th { background: #eee; width: 230px; text-transform: uppercase; font-size: 10px; }
  .assin { display: flex; justify-content: space-between; margin-top: 40px; font-size: 12px; }
  @media print { .no-print { display: none; } body { margin: 10mm; } }
</style></head>
<body>
<div class="no-print"><button onclick="window.print()" style="padding:8px 16px">Imprimir</button> <a href="javascript:history.back()" style="margin-left:10px">Voltar</a></div>
<div class="cab">
  <div class="l1">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
  <div class="l2">{{ cand.cargo if cand else '' }}{% if cand and cand.municipio %} &middot; {{ cand.municipio }}{% endif %}{% if cand and cand.uf %} / {{ cand.uf }}{% endif %}</div>
</div>
<h2>Vis\u00e3o geral do cadastro</h2>
<table>
{% for col in colunas %}
<tr><th>{{ col.replace('_',' ') }}</th><td>{{ p[col] or '' }}</td></tr>
{% endfor %}
</table>
<div class="assin">
  <div>______________________________<br>Respons&aacute;vel pelo cadastro</div>
  <div>______________________________<br>Data: ____/____/______</div>
</div>
</body></html>
""")
print("[3/5] pessoa_imprimir.html (visao geral) criado.")

gravar(os.path.join(TPL, "pessoa_imprimir_contratos.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Contratos da pessoa</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; color: #000; }
  .no-print { margin-bottom: 10px; }
  .cab { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 14px; }
  .cab .l1 { font-size: 18px; font-weight: bold; }
  .cab .l2 { font-size: 13px; }
  h2 { text-align: center; font-size: 18px; margin: 8px 0; }
  p { font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  th, td { border: 1px solid #333; padding: 5px; text-align: left; vertical-align: top; }
  th { background: #eee; }
  .assin { display: flex; justify-content: space-between; margin-top: 45px; font-size: 12px; }
  @media print { .no-print { display: none; } body { margin: 10mm; } }
</style></head>
<body>
<div class="no-print"><button onclick="window.print()" style="padding:8px 16px">Imprimir</button> <a href="javascript:history.back()" style="margin-left:10px">Voltar</a></div>
<div class="cab">
  <div class="l1">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
  <div class="l2">{{ cand.cargo if cand else '' }}</div>
</div>
<h2>Contratos da Pessoa</h2>
<p><b>Pessoa:</b> {{ p.nome or p.id }}{% if p.cpf %} &middot; CPF: {{ p.cpf }}{% endif %}</p>
{% if contratos %}
<table>
  <tr><th>#</th><th>Descri\u00e7\u00e3o</th><th>Tipo</th><th>Valor</th><th>In\u00edcio</th><th>Fim</th><th>Status</th></tr>
  {% for c in contratos %}
  <tr>
    <td>{{ loop.index }}</td>
    <td>{{ c.descricao or '' }}</td>
    <td>{{ c.tipo or '' }}</td>
    <td>{{ c.valor|moeda }}</td>
    <td>{{ c.data_inicio or '' }}</td>
    <td>{{ c.data_fim or '' }}</td>
    <td>{{ c.status or '' }}</td>
  </tr>
  {% endfor %}
</table>
<p style="font-size:11px;margin-top:10px">Total de contratos: {{ contratos|length }}</p>
{% else %}
<p>Nenhum contrato registrado para esta pessoa.</p>
{% endif %}
<div class="assin">
  <div>______________________________<br>Contratante</div>
  <div>______________________________<br>Contratado(a) / Comit\u00ea</div>
</div>
</body></html>
""")
print("[3/5] pessoa_imprimir_contratos.html criado.")

gravar(os.path.join(TPL, "pessoa_imprimir_oficios.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Of\u00edcios da pessoa</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; color: #000; }
  .no-print { margin-bottom: 10px; }
  .cab { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 14px; }
  .cab .l1 { font-size: 18px; font-weight: bold; }
  .cab .l2 { font-size: 13px; }
  h2 { text-align: center; font-size: 18px; margin: 8px 0; }
  p { font-size: 13px; }
  .vazio { color: #666; font-style: italic; }
  @media print { .no-print { display: none; } body { margin: 10mm; } }
</style></head>
<body>
<div class="no-print"><button onclick="window.print()" style="padding:8px 16px">Imprimir</button> <a href="javascript:history.back()" style="margin-left:10px">Voltar</a></div>
<div class="cab">
  <div class="l1">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
  <div class="l2">{{ cand.cargo if cand else '' }}</div>
</div>
<h2>Of\u00edcios da Pessoa</h2>
<p><b>Pessoa:</b> {{ p.nome or p.id }}</p>
{% if oficios %}
<table style="width:100%;border-collapse:collapse;font-size:13px">
  <tr><th style="border:1px solid #333;padding:5px">#</th><th style="border:1px solid #333;padding:5px">Assunto</th><th style="border:1px solid #333;padding:5px">Data</th><th style="border:1px solid #333;padding:5px">Status</th></tr>
  {% for o in oficios %}
  <tr><td style="border:1px solid #333;padding:5px">{{ loop.index }}</td><td style="border:1px solid #333;padding:5px">{{ o.assunto or o.descricao or '' }}</td><td style="border:1px solid #333;padding:5px">{{ o.data or '' }}</td><td style="border:1px solid #333;padding:5px">{{ o.status or '' }}</td></tr>
  {% endfor %}
</table>
{% else %}
<p class="vazio">Nenhum of\u00edcio cadastrado para esta pessoa ainda.</p>
{% endif %}
</body></html>
""")
print("[3/5] pessoa_imprimir_oficios.html criado.")

gravar(os.path.join(TPL, "pessoa_imprimir_recibo.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Recibo eleitoral</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; color: #000; }
  .no-print { margin-bottom: 10px; }
  .cab { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 14px; }
  .cab .l1 { font-size: 18px; font-weight: bold; }
  .cab .l2 { font-size: 13px; }
  h2 { text-align: center; font-size: 18px; margin: 8px 0; }
  .recibo { border: 2px solid #000; padding: 12px; font-size: 13px; }
  .recibo p { margin: 6px 0; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  th, td { border: 1px solid #333; padding: 6px; text-align: left; }
  th { background: #eee; }
  .obs { font-size: 11px; color: #444; margin-top: 10px; }
  .assin { display: flex; justify-content: space-between; margin-top: 45px; font-size: 12px; }
  @media print { .no-print { display: none; } body { margin: 10mm; } }
</style></head>
<body>
<div class="no-print"><button onclick="window.print()" style="padding:8px 16px">Imprimir</button> <a href="javascript:history.back()" style="margin-left:10px">Voltar</a></div>
<div class="cab">
  <div class="l1">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
  <div class="l2">{{ cand.cargo if cand else '' }}{% if cand and cand.municipio %} &middot; {{ cand.municipio }}{% endif %}{% if cand and cand.uf %} / {{ cand.uf }}{% endif %}{% if cand and cand.comite_endereco %} &middot; Comit\u00ea: {{ cand.comite_endereco }}{% endif %}</div>
</div>
<h2>Recibo de Entrega de Material de Campanha</h2>
<div class="recibo">
  <p><b>Recibo N\u00ba:</b> REC-{{ p.id }}-{{ data_hoje.replace('/','') }} &nbsp;&nbsp; <b>Data:</b> {{ data_hoje }}</p>
  <p><b>Eleitor(a):</b> {{ p.nome or '' }}{% if p.cpf %} &middot; CPF: {{ p.cpf }}{% endif %}</p>
  <p>{% if p.endereco %}<b>Endere\u00e7o:</b> {{ p.endereco }}{% if p.numero %}, {{ p.numero }}{% endif %}{% if p.bairro %} &middot; {{ p.bairro }}{% endif %}{% endif %}{% if p.municipio %} &middot; {{ p.municipio }}{% endif %}{% if p.uf %} / {{ p.uf }}{% endif %}{% if p.cep %} &middot; CEP {{ p.cep }}{% endif %}</p>
  {% if p.zona or p.secao %}<p>{% if p.zona %}<b>Zona:</b> {{ p.zona }}{% endif %}{% if p.secao %} &middot; <b>Se\u00e7\u00e3o:</b> {{ p.secao }}{% endif %}</p>{% endif %}
  <p>Recebi do Comit\u00ea de Campanha de <b>{{ cand.nome_urna if cand else 'CARLISE 2233' }}</b> os seguintes materiais de propaganda eleitoral:</p>
  {% if materiais %}
  <table>
    <tr><th>Material</th><th>Quantidade</th><th>Kit / Remessa</th></tr>
    {% for m in materiais %}
    <tr><td>{{ m.material or '' }}</td><td>{{ m.quantidade or '' }}</td><td>{{ m.kit or '' }}</td></tr>
    {% endfor %}
  </table>
  {% else %}
  <table>
    <tr><th style="width:60%">Material</th><th>Quantidade</th></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
  </table>
  {% endif %}
  <p class="obs"><b>Observa\u00e7\u00e3o:</b> entrega de material de propaganda eleitoral permitido pela legisla\u00e7\u00e3o eleitoral vigente (Lei n\u00ba 9.504/1997). \u00c9 vedada a entrega de brindes (camisetas, bon\u00e9s, canecas, chaveiros etc.). Este recibo deve ser guardado junto \u00e0 presta\u00e7\u00e3o de contas.</p>
</div>
<div class="assin">
  <div>______________________________<br>Recebedor(a) &mdash; {{ p.nome or '' }}</div>
  <div>______________________________<br>Entregador(a) / Comit\u00ea</div>
</div>
</body></html>
""")
print("[3/5] pessoa_imprimir_recibo.html (recibo eleitoral) criado.")

# ---------- 4) MENU: nao muda (aba fica dentro da ficha) ----------
print("[4/5] Nenhuma mudanca de menu necessaria - a aba fica dentro da ficha da pessoa.")

# ---------- 5) VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor e abra a ficha de uma pessoa para ver a aba Impressao.")