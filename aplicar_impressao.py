# -*- coding: utf-8 -*-
# Aplica o modulo IMPRESSAO (etiquetas de envio de material de campanha) no CARLISE-2233.
import os, sqlite3, sys, time, shutil, subprocess

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
print("[0/5] Backup: app.py.bak_" + ts)

app_txt = ler(APP)

if "/impressao" in app_txt:
    print("[1/5] app.py ja possui o modulo Impressao. Pulando.")
else:
    ROTAS = '''
# ===== MODULO IMPRESSAO (etiquetas de envio de material de campanha) =====
import sqlite3 as _sq
import os as _os
from datetime import datetime as _dt

_IMPR_BD = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "sistema.db")

def _impr_conn():
    conn = _sq.connect(_IMPR_BD)
    conn.row_factory = _sq.Row
    return conn

def _impr_rows(sql, params=()):
    conn = _impr_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows

def impressao_tabela_existe(nome):
    try:
        r = _impr_rows("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name=?", (nome,))
        return bool(r and r[0]["n"] > 0)
    except Exception:
        return False

def impressao_colunas_pessoas():
    """Descobre sozinho as colunas de endereco da tabela pessoas."""
    try:
        cols = [r["name"] for r in _impr_rows("PRAGMA table_info(pessoas)")]
    except Exception:
        return {}
    low = {c.lower(): c for c in cols}
    def achar(nomes):
        for n in nomes:
            for l, c in low.items():
                if n in l:
                    return c
        return None
    mapa = {}
    mapa["nome"] = achar(["nome", "contato", "pessoa", "apelido"])
    mapa["endereco"] = achar(["logradouro", "endereco", "rua", "av"])
    mapa["numero"] = achar(["numero", "num", "nro"])
    mapa["bairro"] = achar(["bairro", "distrito"])
    mapa["cidade"] = achar(["cidade", "municipio"])
    mapa["uf"] = achar(["uf", "estado", "sigla_uf"])
    mapa["cep"] = achar(["cep", "codigo_postal"])
    mapa["zona"] = achar(["zona", "zona_eleitoral"])
    mapa["secao"] = achar(["secao", "sessao", "secao_eleitoral"])
    mapa["telefone"] = achar(["telefone", "celular", "whatsapp", "tel"])
    return {k: v for k, v in mapa.items() if v}

def impressao_linhas_manuais(texto):
    linhas = []
    for raw in (texto or "").splitlines():
        t = raw.strip()
        if not t:
            continue
        partes = [p.strip() for p in t.split("|")]
        while len(partes) < 5:
            partes.append("")
        linhas.append({
            "nome": partes[0], "endereco": partes[1],
            "bairro": partes[2], "cidade_uf": partes[3], "cep": partes[4],
            "numero": "", "zona": "", "secao": "", "telefone": "",
        })
    return linhas

@app.route("/impressao")
@login_obrigatorio
def impressao():
    mapa = impressao_colunas_pessoas() if impressao_tabela_existe("pessoas") else {}
    pessoas = []
    if mapa:
        try:
            pessoas = _impr_rows("SELECT * FROM pessoas ORDER BY id DESC LIMIT 500")
        except Exception:
            pessoas = []
    return render_template("impressao.html", cand=candidato_ativo(), mapa=mapa, pessoas=pessoas)

@app.route("/impressao/manual", methods=["POST"])
@login_obrigatorio
def impressao_manual():
    texto = request.form.get("texto") or ""
    texto = str(texto).strip()
    etiquetas = impressao_linhas_manuais(texto)
    return render_template("impressao_etiquetas.html", cand=candidato_ativo(),
                           etiquetas=etiquetas,
                           data_hoje=_dt.now().strftime("%d/%m/%Y"))

@app.route("/impressao/pessoas", methods=["POST"])
@login_obrigatorio
def impressao_pessoas():
    ids = request.form.getlist("ids")
    mapa = impressao_colunas_pessoas()
    etiquetas = []
    if ids and mapa:
        rows = []
        try:
            if "todas" in ids:
                rows = _impr_rows("SELECT * FROM pessoas ORDER BY id DESC LIMIT 500")
            elif ids:
                marks = ",".join("?" for _ in ids)
                rows = _impr_rows("SELECT * FROM pessoas WHERE id IN (" + marks + ")", ids)
        except Exception:
            rows = []
        for r in rows:
            def val(campo):
                col = mapa.get(campo)
                if not col:
                    return ""
                try:
                    v = r[col]
                except Exception:
                    return ""
                return str(v) if v is not None else ""
            cidade = val("cidade")
            uf = val("uf")
            cidade_uf = (cidade + "/" + uf) if (cidade or uf) else ""
            etiquetas.append({
                "nome": val("nome"),
                "endereco": val("endereco"),
                "numero": val("numero"),
                "bairro": val("bairro"),
                "cidade_uf": cidade_uf,
                "cep": val("cep"),
                "zona": val("zona"),
                "secao": val("secao"),
                "telefone": val("telefone"),
            })
    return render_template("impressao_etiquetas.html", cand=candidato_ativo(),
                           etiquetas=etiquetas,
                           data_hoje=_dt.now().strftime("%d/%m/%Y"))
'''
    alvo = app_txt.rfind("if __name__")
    if alvo == -1:
        alvo = app_txt.rfind("app.run(")
    if alvo == -1:
        print("[!] Nao achei ponto de insercao. Nada gravado.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTAS + "\n\n" + app_txt[alvo:]
    gravar(APP, app_txt)
    print("[1/5] Rotas do modulo Impressao adicionadas ao app.py.")

# ---------- 2) VERIFICA COLUNAS DE PESSOAS ----------
try:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    tem = conn.execute("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name='pessoas'").fetchone()["n"] > 0
    if tem:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(pessoas)")]
        print("[2/5] Tabela 'pessoas' encontrada. Colunas:", ", ".join(cols))
    else:
        print("[2/5] Tabela 'pessoas' ainda nao existe - voce podera usar a opcao manual de etiquetas.")
        cols = []
    conn.close()
except Exception as e:
    print("[2/5] Nao consegui inspecionar pessoas:", e)
    cols = []

# ---------- 3) TEMPLATE impressao.html ----------
os.makedirs(TPL, exist_ok=True)
gravar(os.path.join(TPL, "impressao.html"), '''{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Impress&#227;o &mdash; Etiquetas de envio</h1>
<p style="color:#666">Etiquetas para envio de material de campanha do Comit&#234; <b>{{ cand.nome_urna or 'CARLISE 2233' }}</b>. Os dados do candidato v&#234;m do m&#243;dulo Configura&#231;&#227;o.</p>

<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <strong>1) Etiquetas das Pessoas cadastradas</strong>
  {% if mapa %}
  <p style="color:#666;font-size:13px;margin-top:6px">Colunas de endere&#231;o detectadas na tabela pessoas: {{ mapa.values()|join(', ') }}</p>
  <form method="post" action="/impressao/pessoas" style="margin-top:10px">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#f5f5f5">
        <th style="padding:6px;text-align:left;width:30px"><input type="checkbox" onchange="marcar_todas(this)" title="Marcar todas"></th>
        <th style="padding:6px;text-align:left">Nome</th>
        <th style="padding:6px;text-align:left">Endere&#231;o</th>
        <th style="padding:6px;text-align:left">Cidade/UF</th>
      </tr>
      {% for p in pessoas %}
      <tr>
        <td style="padding:6px"><input type="checkbox" class="chk-pessoa" name="ids" value="{{ p.id }}"></td>
        <td style="padding:6px">{{ (p[mapa.nome] or '-') if mapa.nome else p.id }}</td>
        <td style="padding:6px">{{ (p[mapa.endereco] or '') if mapa.endereco else '' }}{% if mapa.numero and p[mapa.numero] %}, {{ p[mapa.numero] }}{% endif %}</td>
        <td style="padding:6px">{{ (p[mapa.cidade] or '') if mapa.cidade else '' }}{% if mapa.uf and p[mapa.uf] %}/{{ p[mapa.uf] }}{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
    <div style="margin-top:12px;display:flex;gap:8px">
      <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Imprimir selecionadas</button>
      <button type="submit" name="ids" value="todas" style="background:#eee;color:#333;padding:8px 16px;border-radius:8px;border:1px solid #ccc;cursor:pointer">Imprimir todas</button>
    </div>
  </form>
  {% else %}
  <p style="color:#999;margin-top:8px">N&#227;o encontrei colunas de endere&#231;o na tabela pessoas (ou a tabela ainda n&#227;o existe). Use a op&#231;&#227;o manual abaixo.</p>
  {% endif %}
</div>

<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <strong>2) Etiquetas manuais (digitar ou colar)</strong>
  <p style="color:#666;font-size:13px;margin-top:6px">Uma etiqueta por linha, campos separados por |. Formato:<br>
  <code>Nome | Endere&#231;o e n&#250;mero | Bairro | Cidade/UF | CEP</code></p>
  <form method="post" action="/impressao/manual">
    <textarea name="texto" rows="6" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box" placeholder="Maria da Silva | Rua das Flores, 123 | Centro | Curitiba/PR | 80000-000"> </textarea>
    <div style="margin-top:12px">
      <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Gerar etiquetas</button>
    </div>
  </form>
</div>
</div>
<script>
function marcar_todas(cb){
  var cxs = document.querySelectorAll('.chk-pessoa');
  for (var i=0;i<cxs.length;i++){ cxs[i].checked = cb.checked; }
}
</script>
{% endblock %}
''')
print("[3/5] Template impressao.html criado.")

# ---------- 4) TEMPLATE impressao_etiquetas.html (pagina de impressao) ----------
gravar(os.path.join(TPL, "impressao_etiquetas.html"), '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Etiquetas de envio</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: Arial, sans-serif; margin: 0; padding: 12px; background: #fafafa; }
  .no-print { margin-bottom: 12px; }
  .btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #999; background: #0050FF; color: #fff; text-decoration: none; cursor: pointer; font-size: 14px; display: inline-block; }
  .btn-cinza { background: #eee; color: #333; border-color: #ccc; margin-right: 6px; }
  .info { margin-left: 12px; font-size: 13px; color: #555; }
  .grade { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; }
  body.fmt-2 .grade { grid-template-columns: repeat(2, 1fr); }
  body.fmt-1 .grade { grid-template-columns: repeat(1, 1fr); }
  .etiqueta { border: 1px solid #999; border-radius: 3px; padding: 3mm 4mm; min-height: 44mm; break-inside: avoid; page-break-inside: avoid; background: #fff; }
  .cab { font-size: 9px; letter-spacing: 1px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 2px; margin-bottom: 4px; text-transform: uppercase; }
  .cand { font-size: 13px; font-weight: bold; color: #0050FF; margin-bottom: 6px; }
  .dest { font-size: 12px; margin: 2px 0; }
  .dest b { font-size: 13px; }
  .end, .cidade, .extra, .rodape { font-size: 11px; color: #333; margin: 1px 0; }
  .rodape { margin-top: 6px; border-top: 1px dashed #ccc; padding-top: 3px; font-size: 9px; color: #666; }
  .vazio { color: #999; font-style: italic; }
  @media print {
    .no-print { display: none !important; }
    body { padding: 0; background: #fff; }
    @page { margin: 8mm; }
    .etiqueta { border-color: #000; }
  }
</style>
</head>
<body class="fmt-3">
  <div class="no-print">
    <a class="btn btn-cinza" href="/impressao">&larr; Voltar</a>
    <button class="btn" onclick="window.print()">Imprimir etiquetas</button>
    <label class="info">Formato:
      <select onchange="document.body.className=this.value">
        <option value="fmt-3" selected>3 por linha</option>
        <option value="fmt-2">2 por linha</option>
        <option value="fmt-1">1 por linha</option>
      </select>
    </label>
    <span class="info">Total: {{ etiquetas|length }} etiqueta(s)</span>
  </div>
  <div class="grade">
    {% for e in etiquetas %}
    <div class="etiqueta">
      <div class="cab">Comit&#234; de Campanha</div>
      <div class="cand">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
      <div class="dest">Para: <b>{{ e.nome }}</b></div>
      <div class="end">{{ e.endereco }}{% if e.numero %}, {{ e.numero }}{% endif %}{% if e.bairro %} &middot; {{ e.bairro }}{% endif %}</div>
      <div class="cidade">{% if e.cidade_uf %}{{ e.cidade_uf }}{% endif %}{% if e.cidade_uf and e.cep %} &middot; {% endif %}{% if e.cep %}CEP {{ e.cep }}{% endif %}</div>
      {% if e.zona or e.secao or e.telefone %}<div class="extra">{% if e.zona %}Zona {{ e.zona }}{% endif %}{% if e.secao %} &middot; Se&#231;&#227;o {{ e.secao }}{% endif %}{% if e.telefone %} &middot; {{ e.telefone }}{% endif %}</div>{% endif %}
      <div class="rodape">{{ cand.cargo if cand else 'Cargo' }} &middot; Material de campanha &middot; Data: {{ data_hoje }}</div>
    </div>
    {% else %}
    <div class="vazio">Nenhuma etiqueta gerada. Volte e informe ao menos um destinat&#225;rio.</div>
    {% endfor %}
  </div>
</body>
</html>
''')
print("[4/5] Template impressao_etiquetas.html criado.")

# ---------- 5) MENU no base.html ----------
base_p = os.path.join(TPL, "base.html")
if os.path.exists(base_p):
    base_txt = ler(base_p)
    if "/impressao" in base_txt:
        print("[5/5] base.html ja possui o menu Impressao. Pulando.")
    else:
        idx = base_txt.find('<a href="/configuracao"')
        if idx == -1:
            idx = base_txt.find('<a href="/pessoas"')
        if idx != -1:
            fim_li = base_txt.find("\n", idx)
            if fim_li != -1:
                base_txt = base_txt[:fim_li] + ' <a href="/impressao" class="{{ \'ativo\' if request.path.startswith(\'/impressao\') else \'\' }}">Impress&#227;o</a>' + base_txt[fim_li:]
                gravar(base_p, base_txt)
                print("[5/5] Menu Impressao adicionado ao base.html.")
            else:
                print("[5/5] Nao consegui inserir o menu.")
        else:
            print("[5/5] Nao achei o menu para inserir - voce acessa pela URL /impressao.")
else:
    print("[5/5] base.html nao encontrado.")

# ---------- VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor (pare o python app.py atual e rode de novo) e acesse /impressao.")