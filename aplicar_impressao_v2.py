# -*- coding: utf-8 -*-
# Aplica o MODULO IMPRESSAO V2 (correspondencia + kit com codigo de barras e declaracao de transporte) no CARLISE-2233.
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
print("[0/6] Backup: app.py.bak_" + ts)

app_txt = ler(APP)

# ---------- 1) REMOVE MODULO IMPRESSAO ANTERIOR (se existir) ----------
if "# ===== MODULO IMPRESSAO V2" in app_txt:
    print("[1/6] Impressao V2 ja aplicado. Pulando insercao.")
else:
    ini = app_txt.find("# ===== MODULO IMPRESSAO")
    if ini != -1:
        fim = app_txt.find("if __name__", ini)
        if fim != -1:
            app_txt = app_txt[:ini] + "\n\n" + app_txt[fim:]
            print("[1/6] Bloco antigo de impressao removido.")
        else:
            print("[1/6] Aviso: nao achei o fim do bloco antigo - mantive como esta.")
    else:
        print("[1/6] Nenhum bloco antigo de impressao - seguindo.")

    ROTAS = '''
# ===== MODULO IMPRESSAO V2 (correspondencia + kit com codigo de barras e declaracao de transporte) =====
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
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()

def _impr_exec(sql, params=()):
    conn = _impr_conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

def _impr_cols(tabela):
    try:
        return [r["name"] for r in _impr_rows("PRAGMA table_info(" + tabela + ")")]
    except Exception:
        return []

def _impr_garante_colunas():
    for tabela, extras in (
        ("pessoas", [("data_aniversario","TEXT DEFAULT ''"),("demandas","TEXT DEFAULT ''"),
                     ("categoria","TEXT DEFAULT ''"),("observacao","TEXT DEFAULT ''")]),
        ("candidato", [("comite_endereco","TEXT DEFAULT ''"),("comite_telefone","TEXT DEFAULT ''")]),
    ):
        try:
            cols = _impr_cols(tabela)
            for nome, tipo in extras:
                if nome not in cols:
                    _impr_exec("ALTER TABLE " + tabela + " ADD COLUMN " + nome + " " + tipo)
        except Exception:
            pass

def _impr_mapa_pessoas():
    cols = _impr_cols("pessoas")
    if not cols:
        return {}
    low = {c.lower(): c for c in cols}
    def achar(nomes):
        for n in nomes:
            for l, c in low.items():
                if n in l:
                    return c
        return None
    mapa = {
        "id": achar(["id"]),
        "nome": achar(["nome","contato","pessoa","apelido"]),
        "endereco": achar(["logradouro","endereco","rua","av"]),
        "numero": achar(["numero","num","nro"]),
        "bairro": achar(["bairro","distrito"]),
        "cidade": achar(["cidade","municipio"]),
        "uf": achar(["uf","estado","sigla_uf"]),
        "cep": achar(["cep","codigo_postal"]),
        "zona": achar(["zona","zona_eleitoral"]),
        "secao": achar(["secao","sessao","secao_eleitoral"]),
        "telefone": achar(["telefone","celular","whatsapp","tel"]),
        "aniversario": achar(["aniversario","nascimento","data_nasc"]),
        "demandas": achar(["demandas","demanda","assunto","correspondencia"]),
        "categoria": achar(["categoria","tipo","grupo"]),
        "observacao": achar(["observacao","obs","notas"]),
    }
    return {k: v for k, v in mapa.items() if v}

def _impr_val(r, mapa, campo):
    col = mapa.get(campo)
    if not col:
        return ""
    try:
        v = r[col]
    except Exception:
        return ""
    return str(v) if v is not None else ""

def _impr_pessoas_filtra(request):
    mapa = _impr_mapa_pessoas()
    nome_col = mapa.get("nome") or "id"
    try:
        rows = _impr_rows("SELECT * FROM pessoas ORDER BY " + nome_col + " COLLATE NOCASE LIMIT 2000")
    except Exception:
        rows = []
    mes = (request.args.get("mes") or "").strip()
    busca = (request.args.get("busca") or "").strip().lower()
    categoria = (request.args.get("categoria") or "").strip().lower()
    so_demanda = request.args.get("so_demanda") == "1"
    out = []
    for r in rows:
        nome = _impr_val(r, mapa, "nome")
        if busca and busca not in nome.lower():
            continue
        if categoria and categoria not in _impr_val(r, mapa, "categoria").lower():
            continue
        if so_demanda and not _impr_val(r, mapa, "demandas"):
            continue
        if mes:
            mm = mes.zfill(2)
            aniv = _impr_val(r, mapa, "aniversario")
            if not (("-" + mm + "-") in aniv or ("/" + mm + "/") in aniv):
                continue
        out.append(r)
    return out

def _impr_aniv_curto(aniv):
    for sep in ("-", "/"):
        if sep in aniv:
            partes = aniv.split(sep)
            if len(partes) == 3:
                if len(partes[0]) == 4:
                    return partes[2] + "/" + partes[1]
                return partes[0] + "/" + partes[1]
    return ""

def _impr_etqs_pessoas(ids, mapa):
    etqs = []
    rows = []
    nome_col = mapa.get("nome") or "id"
    try:
        if ids and ids[0] == "todas":
            rows = _impr_rows("SELECT * FROM pessoas ORDER BY " + nome_col + " COLLATE NOCASE LIMIT 2000")
        elif ids:
            marks = ",".join("?" for _ in ids)
            rows = _impr_rows("SELECT * FROM pessoas WHERE id IN (" + marks + ")", ids)
    except Exception:
        rows = []
    for r in rows:
        cidade = _impr_val(r, mapa, "cidade")
        uf = _impr_val(r, mapa, "uf")
        etqs.append({
            "id": r["id"],
            "nome": _impr_val(r, mapa, "nome"),
            "endereco": _impr_val(r, mapa, "endereco"),
            "numero": _impr_val(r, mapa, "numero"),
            "bairro": _impr_val(r, mapa, "bairro"),
            "cidade_uf": (cidade + "/" + uf) if (cidade or uf) else "",
            "cep": _impr_val(r, mapa, "cep"),
            "zona": _impr_val(r, mapa, "zona"),
            "secao": _impr_val(r, mapa, "secao"),
            "telefone": _impr_val(r, mapa, "telefone"),
            "aniversario": _impr_aniv_curto(_impr_val(r, mapa, "aniversario")),
            "demandas": _impr_val(r, mapa, "demandas"),
            "categoria": _impr_val(r, mapa, "categoria"),
        })
    return etqs

def _impr_code39_svg(texto, altura=42):
    pad = {
        '0':'000110100','1':'100100001','2':'001100001','3':'101100000',
        '4':'000110001','5':'100110000','6':'001110000','7':'000100101',
        '8':'100100100','9':'001100100','A':'100001001','B':'001001001',
        'C':'101001000','D':'000011001','E':'100011000','F':'001011000',
        'G':'000001101','H':'100001100','I':'001001100','J':'000011100',
        'K':'100000011','L':'001000011','M':'101000010','N':'000010011',
        'O':'100010010','P':'001010010','Q':'000000111','R':'100000110',
        'S':'001000110','T':'000010110','U':'110000001','V':'011000001',
        'W':'111000000','X':'010010001','Y':'110010000','Z':'011010000',
        '-':'010000101','.':'110000100',' ':'011000100','$':'010101000',
        '/':'010100010','+':'010001010','%':'000101010','*':'010010100',
    }
    texto = texto.upper()
    chars = [c for c in texto if c in pad]
    if not chars:
        chars = ['0']
    seq = ['*'] + chars + ['*']
    x = 4
    rets = []
    for ch in seq:
        for i, mod in enumerate(pad[ch]):
            w = 3 if mod == '1' else 1
            if i % 2 == 0:
                rets.append('<rect x="' + str(x) + '" y="0" width="' + str(w) + '" height="' + str(altura) + '" fill="#000"/>')
            x += w + 1
        x += 1
    largura = x + 4
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="' + str(largura) + '" height="' + str(altura) +
           '" style="background:#fff;display:block;max-width:100%">' + "".join(rets) + '</svg>')
    return svg

@app.route("/impressao")
@login_obrigatorio
def impressao():
    _impr_garante_colunas()
    return render_template("impressao.html", cand=candidato_ativo())

@app.route("/impressao/correspondencia", methods=["GET","POST"])
@login_obrigatorio
def impressao_correspondencia():
    _impr_garante_colunas()
    mapa = _impr_mapa_pessoas()
    pessoas = _impr_pessoas_filtra(request)
    if request.method == "POST":
        if request.form.get("todas") == "1":
            ids = ["todas"]
        else:
            ids = request.form.getlist("ids")
        etqs = _impr_etqs_pessoas(ids, mapa)
        return render_template("impressao_etiquetas_correspondencia.html", cand=candidato_ativo(),
                               etiquetas=etqs, data_hoje=_dt.now().strftime("%d/%m/%Y"))
    return render_template("impressao_correspondencia.html", cand=candidato_ativo(),
                           pessoas=pessoas, mapa=mapa)

@app.route("/impressao/kit", methods=["GET","POST"])
@login_obrigatorio
def impressao_kit():
    _impr_garante_colunas()
    mapa = _impr_mapa_pessoas()
    pessoas = _impr_pessoas_filtra(request)
    if request.method == "POST":
        if request.form.get("todas") == "1":
            ids = ["todas"]
        else:
            ids = request.form.getlist("ids")
        etqs = _impr_etqs_pessoas(ids, mapa)
        cand = candidato_ativo() or {}
        modelo = request.form.get("modelo")
        if modelo not in ("correios", "transportadora"):
            modelo = "correios"
        conteudo = sane(request.form.get("conteudo") or "Material de campanha")
        quantidade = sane(request.form.get("quantidade") or "1")
        peso = sane(request.form.get("peso") or "")
        valor = sane(request.form.get("valor") or "")
        seq_atual = int(sane(request.form.get("seq") or "1") or 1)
        sigla_base = (cand or {}).get("nome_urna") or "CARLISE"
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
        return render_template("impressao_etiquetas_kits.html", cand=cand,
                               etiquetas=etqs, data_hoje=_dt.now().strftime("%d/%m/%Y"))
    return render_template("impressao_kits.html", cand=candidato_ativo(),
                           pessoas=pessoas, mapa=mapa)

@app.route("/pessoas/<int:pid>/correspondencia", methods=["POST"])
@login_obrigatorio
def pessoas_correspondencia(pid):
    _impr_garante_colunas()
    alterar("UPDATE pessoas SET data_aniversario=%s, demandas=%s, categoria=%s, observacao=%s WHERE id=%s",
            (sane(request.form.get("data_aniversario")),
             sane(request.form.get("demandas")),
             norm_txt(request.form.get("categoria")),
             sane(request.form.get("observacao")), pid))
    flash("Correspondencia salva na ficha da pessoa.", "ok")
    return redirect(request.referrer or url_for("pessoas"))
'''
    alvo = app_txt.find("if __name__")
    if alvo == -1:
        alvo = app_txt.find("app.run(")
    if alvo == -1:
        print("[!] Nao achei ponto de insercao. Nada gravado.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTAS + "\n\n" + app_txt[alvo:]
    gravar(APP, app_txt)
    print("[1/6] Rotas do Impressao V2 adicionadas ao app.py.")

    # ---------- 2) CAMPOS DO COMITE NO MODULO CONFIGURACAO ----------
    if '"comite_endereco"' not in app_txt:
        app_txt = ler(APP)
        antigo = '"data_nascimento","email","telefone","site","biografia",'
        novo = '"data_nascimento","email","telefone","site","biografia","comite_endereco","comite_telefone",'
        if antigo in app_txt:
            app_txt = app_txt.replace(antigo, novo)
            gravar(APP, app_txt)
            print("[2/6] Campos do comite adicionados ao cadastro do candidato.")
        else:
            print("[2/6] Aviso: nao achei a lista de campos do candidato - sigo com os campos que existem.")
    else:
        print("[2/6] Campos do comite ja presentes.")

# ---------- 3) COLUNAS NO BANCO ----------
try:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    for tabela, extras in (
        ("pessoas", [("data_aniversario","TEXT DEFAULT ''"),("demandas","TEXT DEFAULT ''"),
                     ("categoria","TEXT DEFAULT ''"),("observacao","TEXT DEFAULT ''")]),
        ("candidato", [("comite_endereco","TEXT DEFAULT ''"),("comite_telefone","TEXT DEFAULT ''")]),
    ):
        exist = [r["name"] for r in conn.execute("PRAGMA table_info(" + tabela + ")")] if conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone()[0] else []
        for nome, tipo in extras:
            if nome not in exist:
                conn.execute("ALTER TABLE " + tabela + " ADD COLUMN " + nome + " " + tipo)
    conn.commit()
    cols_p = [r["name"] for r in conn.execute("PRAGMA table_info(pessoas)")]
    conn.close()
    print("[3/6] Colunas verificadas/adicionadas. pessoas:", ", ".join(cols_p))
except Exception as e:
    print("[3/6] Aviso ao verificar banco:", e)

# ---------- 4) TEMPLATES ----------
os.makedirs(TPL, exist_ok=True)

gravar(os.path.join(TPL, "impressao.html"), """{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Impress&#227;o</h1>
<p style="color:#666">Dados do candidato v&#234;m do m&#243;dulo Configura&#231;&#227;o: <b>{{ cand.nome_urna if cand else 'CARLISE 2233' }}</b> ({{ cand.numero_candidatura if cand else '2233' }}).</p>
<div style="display:flex;flex-wrap:wrap;gap:16px;margin-top:16px">
  <div style="flex:1;min-width:260px;border:1px solid #ddd;border-radius:12px;padding:18px">
    <div style="font-size:22px">&#9993;</div>
    <h3 style="margin:8px 0">Correspond&#234;ncia</h3>
    <p style="color:#555;font-size:14px">Etiquetas de carta por pessoa, com <b>anivers&#225;rio</b>, <b>demandas</b> e <b>categoria</b> — filtros por aniversariantes do m&#234;s ou por demanda.</p>
    <a href="/impressao/correspondencia" style="background:#0050FF;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;display:inline-block;margin-top:8px">Abrir Correspond&#234;ncia</a>
  </div>
  <div style="flex:1;min-width:260px;border:1px solid #ddd;border-radius:12px;padding:18px">
    <div style="font-size:22px">&#128230;</div>
    <h3 style="margin:8px 0">Kit / Envio de Material</h3>
    <p style="color:#555;font-size:14px">Etiqueta de envio com <b>REMETENTE, DESTINAT&#193;RIO, C&#211;DIGO DE BARRAS</b> e <b>DECLARA&#199;&#195;O DE TRANSPORTE</b> (Correios ou Transportadora).</p>
    <a href="/impressao/kit" style="background:#0050FF;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;display:inline-block;margin-top:8px">Abrir Kit / Envio</a>
  </div>
</div>
</div>
{% endblock %}
""")
print("[4/6] impressao.html (seletor) criado.")

gravar(os.path.join(TPL, "impressao_correspondencia.html"), """{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Correspond&#234;ncia &mdash; Etiquetas</h1>
<p style="color:#666">Marque as pessoas e imprima. Filtros opcionais: m&#234;s de anivers&#225;rio, busca, categoria e s&#243; quem tem demanda.</p>
<form method="get" action="/impressao/correspondencia" style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0">
  <select name="mes" style="padding:8px;border-radius:8px;border:1px solid #ccc">
    <option value="">M&#234;s de anivers&#225;rio (todos)</option>
    {% for m in range(1,13) %}<option value="{{ '%02d' % m }}" {% if request.args.get('mes') == '%02d' % m %}selected{% endif %}>{{ '%02d' % m }}</option>{% endfor %}
  </select>
  <input type="text" name="busca" value="{{ request.args.get('busca','') }}" placeholder="Buscar nome" style="padding:8px;border-radius:8px;border:1px solid #ccc">
  <input type="text" name="categoria" value="{{ request.args.get('categoria','') }}" placeholder="Categoria" style="padding:8px;border-radius:8px;border:1px solid #ccc">
  <label style="align-self:center"><input type="checkbox" name="so_demanda" value="1" {% if request.args.get('so_demanda') == '1' %}checked{% endif %}> S&#243; quem tem demanda</label>
  <button type="submit" style="background:#0050FF;color:#fff;padding:8px 14px;border-radius:8px;border:none;cursor:pointer">Filtrar</button>
  <a href="/impressao/correspondencia" style="align-self:center;color:#555">Limpar</a>
</form>

<form method="post" action="/impressao/correspondencia">
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:#f5f5f5">
      <th style="padding:6px;width:30px;text-align:left"><input type="checkbox" onchange="marcar_todas(this)"></th>
      <th style="padding:6px;text-align:left">Nome</th>
      <th style="padding:6px;text-align:left">Anivers&#225;rio</th>
      <th style="padding:6px;text-align:left">Categoria</th>
      <th style="padding:6px;text-align:left">Demandas</th>
    </tr>
    {% for p in pessoas %}
    <tr style="border-top:1px solid #eee">
      <td style="padding:6px"><input type="checkbox" class="chk-p" name="ids" value="{{ p.id }}"></td>
      <td style="padding:6px">{{ (p[mapa.nome] if mapa.nome else '') or '-' }}</td>
      <td style="padding:6px">{{ (p[mapa.aniversario] if mapa.aniversario else '') or '' }}</td>
      <td style="padding:6px">{{ (p[mapa.categoria] if mapa.categoria else '') or '' }}</td>
      <td style="padding:6px">{{ (p[mapa.demandas] if mapa.demandas else '') or '' }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5" style="padding:14px;color:#999">Nenhuma pessoa encontrada com esses filtros.</td></tr>
    {% endfor %}
  </table>
  <div style="margin-top:12px;display:flex;gap:8px">
    <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Imprimir selecionadas</button>
    <button type="submit" name="todas" value="1" style="background:#eee;color:#333;padding:8px 16px;border-radius:8px;border:1px solid #ccc;cursor:pointer">Imprimir todas</button>
    <a href="/impressao" style="align-self:center;color:#555">&larr; Voltar</a>
  </div>
</form>
</div>
<script>
function marcar_todas(cb){ var c = document.querySelectorAll('.chk-p'); for (var i=0;i<c.length;i++){ c[i].checked = cb.checked; } }
</script>
{% endblock %}
""")
print("[4/6] impressao_correspondencia.html criado.")

gravar(os.path.join(TPL, "impressao_kits.html"), """{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Kit / Envio de Material &mdash; Etiquetas</h1>
<p style="color:#666">Etiqueta de envio com REMETENTE, DESTINAT&#193;RIO, C&#211;DIGO DE BARRAS e DECLARA&#199;&#195;O DE TRANSPORTE. O c&#243;digo de barras usa: sigla + n&#250;mero do candidato, ID da pessoa e n&#250;mero sequencial do envio.</p>
<form method="get" action="/impressao/kit" style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0">
  <input type="text" name="busca" value="{{ request.args.get('busca','') }}" placeholder="Buscar nome" style="padding:8px;border-radius:8px;border:1px solid #ccc">
  <select name="mes" style="padding:8px;border-radius:8px;border:1px solid #ccc">
    <option value="">M&#234;s de anivers&#225;rio (todos)</option>
    {% for m in range(1,13) %}<option value="{{ '%02d' % m }}" {% if request.args.get('mes') == '%02d' % m %}selected{% endif %}>{{ '%02d' % m }}</option>{% endfor %}
  </select>
  <input type="text" name="categoria" value="{{ request.args.get('categoria','') }}" placeholder="Categoria" style="padding:8px;border-radius:8px;border:1px solid #ccc">
  <button type="submit" style="background:#0050FF;color:#fff;padding:8px 14px;border-radius:8px;border:none;cursor:pointer">Filtrar</button>
  <a href="/impressao/kit" style="align-self:center;color:#555">Limpar</a>
</form>

<form method="post" action="/impressao/kit">
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:#f5f5f5">
      <th style="padding:6px;width:30px;text-align:left"><input type="checkbox" onchange="marcar_todas(this)"></th>
      <th style="padding:6px;text-align:left">Nome</th>
      <th style="padding:6px;text-align:left">Endere&#231;o</th>
      <th style="padding:6px;text-align:left">Cidade/UF</th>
    </tr>
    {% for p in pessoas %}
    <tr style="border-top:1px solid #eee">
      <td style="padding:6px"><input type="checkbox" class="chk-p" name="ids" value="{{ p.id }}"></td>
      <td style="padding:6px">{{ (p[mapa.nome] if mapa.nome else '') or '-' }}</td>
      <td style="padding:6px">{{ (p[mapa.endereco] if mapa.endereco else '') or '' }}{% if mapa.numero and p[mapa.numero] %}, {{ p[mapa.numero] }}{% endif %}</td>
      <td style="padding:6px">{{ (p[mapa.cidade] if mapa.cidade else '') or '' }}{% if mapa.uf and p[mapa.uf] %}/{{ p[mapa.uf] }}{% endif %}</td>
    </tr>
    {% else %}
    <tr><td colspan="4" style="padding:14px;color:#999">Nenhuma pessoa encontrada.</td></tr>
    {% endfor %}
  </table>

  <div style="border:1px solid #ddd;border-radius:10px;padding:14px;margin-top:14px">
    <strong>Dados do envio e da declara&#231;&#227;o de transporte</strong>
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px">
      <input type="text" name="conteudo" value="Material de campanha" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc" placeholder="Conte&#250;do">
      <input type="text" name="quantidade" value="1" style="flex:1;min-width:90px;padding:8px;border-radius:8px;border:1px solid #ccc" placeholder="Qtd./volumes">
      <input type="text" name="peso" value="" style="flex:1;min-width:110px;padding:8px;border-radius:8px;border:1px solid #ccc" placeholder="Peso (g ou kg)">
      <input type="text" name="valor" value="" style="flex:1;min-width:120px;padding:8px;border-radius:8px;border:1px solid #ccc" placeholder="Valor declarado (R$)">
      <input type="text" name="seq" value="1" style="flex:1;min-width:110px;padding:8px;border-radius:8px;border:1px solid #ccc" placeholder="Sequencial inicial">
    </div>
    <div style="margin-top:10px">
      <strong>Modelo da declara&#231;&#227;o:</strong>
      <label style="margin-left:12px"><input type="radio" name="modelo" value="correios" checked> Correios</label>
      <label style="margin-left:12px"><input type="radio" name="modelo" value="transportadora"> Transportadora</label>
    </div>
  </div>

  <div style="margin-top:14px;display:flex;gap:8px">
    <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Imprimir selecionadas</button>
    <button type="submit" name="todas" value="1" style="background:#eee;color:#333;padding:8px 16px;border-radius:8px;border:1px solid #ccc;cursor:pointer">Imprimir todas</button>
    <a href="/impressao" style="align-self:center;color:#555">&larr; Voltar</a>
  </div>
</form>
</div>
<script>
function marcar_todas(cb){ var c = document.querySelectorAll('.chk-p'); for (var i=0;i<c.length;i++){ c[i].checked = cb.checked; } }
</script>
{% endblock %}
""")
print("[4/6] impressao_kits.html criado.")

gravar(os.path.join(TPL, "impressao_etiquetas_correspondencia.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Etiquetas de correspondencia</title>
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
  .end, .cidade, .extra, .linha-corpo { font-size: 11px; color: #333; margin: 2px 0; }
  .linha-corpo { border-top: 1px dashed #ddd; padding-top: 4px; margin-top: 4px; }
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
    <a class="btn btn-cinza" href="/impressao/correspondencia">&larr; Voltar</a>
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
      <div class="cab">Correspond&#234;ncia &mdash; Comit&#234; de Campanha</div>
      <div class="cand">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
      <div class="dest">Para: <b>{{ e.nome or '-' }}</b></div>
      <div class="end">{{ e.endereco }}{% if e.numero %}, {{ e.numero }}{% endif %}{% if e.bairro %} &middot; {{ e.bairro }}{% endif %}</div>
      <div class="cidade">{% if e.cidade_uf %}{{ e.cidade_uf }}{% endif %}{% if e.cidade_uf and e.cep %} &middot; {% endif %}{% if e.cep %}CEP {{ e.cep }}{% endif %}</div>
      {% if e.zona or e.secao or e.telefone %}<div class="extra">{% if e.zona %}Zona {{ e.zona }}{% endif %}{% if e.secao %} &middot; Se&#231;&#227;o {{ e.secao }}{% endif %}{% if e.telefone %} &middot; {{ e.telefone }}{% endif %}</div>{% endif %}
      <div class="linha-corpo">
        {% if e.aniversario %}Anivers&#225;rio: <b>{{ e.aniversario }}</b><br>{% endif %}
        {% if e.demandas %}Demanda/Assunto: <b>{{ e.demandas }}</b><br>{% endif %}
        {% if e.categoria %}Categoria: {{ e.categoria }}{% endif %}
        {% if not e.aniversario and not e.demandas and not e.categoria %}Correspond&#234;ncia geral{% endif %}
      </div>
      <div class="rodape">Enviado por: {{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ data_hoje }}</div>
    </div>
    {% else %}
    <div class="vazio">Nenhuma etiqueta gerada.</div>
    {% endfor %}
  </div>
</body>
</html>
""")
print("[4/6] impressao_etiquetas_correspondencia.html criado.")

gravar(os.path.join(TPL, "impressao_etiquetas_kits.html"), """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Etiquetas de envio de material</title>
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
  .etiqueta { border: 1px solid #999; border-radius: 3px; padding: 3mm 4mm; min-height: 52mm; break-inside: avoid; page-break-inside: avoid; background: #fff; font-size: 11px; }
  .cab { font-size: 9px; letter-spacing: 1px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 2px; margin-bottom: 4px; text-transform: uppercase; }
  .bloco { border: 1px solid #ccc; border-radius: 3px; padding: 4px; margin: 4px 0; }
  .rot { font-size: 8px; color: #888; text-transform: uppercase; letter-spacing: .5px; }
  .rem { font-weight: bold; color: #0050FF; font-size: 12px; }
  .dest b { font-size: 12px; }
  .codigo { text-align: center; margin: 4px 0; }
  .codigo .num { font-family: monospace; font-size: 11px; margin-top: 2px; letter-spacing: 1px; }
  .dec { border: 1px solid #999; border-radius: 3px; padding: 4px; margin-top: 4px; }
  .dec .rot { color: #c00; font-weight: bold; }
  .linhas { font-size: 10px; }
  .ass { margin-top: 5px; font-size: 9px; color: #444; }
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
    <a class="btn btn-cinza" href="/impressao/kit">&larr; Voltar</a>
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
      <div class="cab">Comit&#234; de Campanha &mdash; Envio de Material</div>

      <div class="bloco">
        <div class="rot">Remetente</div>
        <div class="rem">{{ cand.nome_urna if cand else 'CARLISE 2233' }} &middot; {{ cand.numero_candidatura if cand else '2233' }}</div>
        <div>{{ cand.cargo if cand else 'Cargo' }}{% if cand and cand.municipio %} &middot; {{ cand.municipio }}{% endif %}{% if cand and cand.uf %} / {{ cand.uf }}{% endif %}</div>
        {% if cand and cand.comite_endereco %}<div>{{ cand.comite_endereco }}</div>{% endif %}
        {% if cand and cand.comite_telefone %}<div>Tel: {{ cand.comite_telefone }}</div>{% endif %}
      </div>

      <div class="bloco">
        <div class="rot">Destinat&#225;rio</div>
        <div class="dest"><b>{{ e.nome or '-' }}</b></div>
        <div>{{ e.endereco }}{% if e.numero %}, {{ e.numero }}{% endif %}{% if e.bairro %} &middot; {{ e.bairro }}{% endif %}</div>
        <div>{% if e.cidade_uf %}{{ e.cidade_uf }}{% endif %}{% if e.cidade_uf and e.cep %} &middot; {% endif %}{% if e.cep %}CEP {{ e.cep }}{% endif %}</div>
        {% if e.zona or e.secao or e.telefone %}<div>{% if e.zona %}Zona {{ e.zona }}{% endif %}{% if e.secao %} &middot; Se&#231;&#227;o {{ e.secao }}{% endif %}{% if e.telefone %} &middot; {{ e.telefone }}{% endif %}</div>{% endif %}
      </div>

      <div class="codigo">
        {{ e.barra|safe }}
        <div class="num">N&#186;: {{ e.codigo }}</div>
      </div>

      <div class="dec">
        <div class="rot">Declara&#231;&#227;o de Transporte{% if e.modelo == 'correios' %} &mdash; Correios{% else %} &mdash; Transportadora{% endif %}</div>
        {% if e.modelo == 'correios' %}
        <div class="linhas">Conte&#250;do: <b>{{ e.conteudo }}</b> &middot; Qtd.: <b>{{ e.quantidade }}</b><br>
        Valor declarado: {{ e.valor or '-' }} &middot; Peso: {{ e.peso or '-' }}<br>
        N&#186; do objeto: {{ e.codigo }} &middot; Data: {{ data_hoje }}</div>
        {% else %}
        <div class="linhas">Conte&#250;do: <b>{{ e.conteudo }}</b><br>
        Volumes: <b>{{ e.quantidade }}</b> &middot; Peso total: {{ e.peso or '-' }} &middot; Valor: {{ e.valor or '-' }}<br>
        Data: {{ data_hoje }}</div>
        {% endif %}
        <div class="ass">Expedidor: ______________________ &nbsp;&nbsp; Recebedor: ______________________</div>
      </div>
    </div>
    {% else %}
    <div class="vazio">Nenhuma etiqueta gerada.</div>
    {% endfor %}
  </div>
</body>
</html>
""")
print("[4/6] impressao_etiquetas_kits.html criado.")

# ---------- 5) FICHA DA PESSOA: secao Correspondencia e Impressao ----------
ficha_p = os.path.join(TPL, "ficha_pessoa.html")
if os.path.exists(ficha_p):
    ficha = ler(ficha_p)
    if "pessoas_correspondencia" not in ficha and "Correspond&#234;ncia e Impress&#227;o" not in ficha:
        bloco = """

<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <h3>Correspond&#234;ncia e Impress&#227;o</h3>
  <form method="post" action="/pessoas/{{ request.view_args.get('id') or request.view_args.get('pid') or request.view_args.get('pessoa_id') }}/correspondencia">
    <div style="display:flex;flex-wrap:wrap;gap:10px">
      <input type="date" name="data_aniversario" value="{{ p.data_aniversario or pessoa.data_aniversario or '' }}" placeholder="Data de anivers&#225;rio" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc">
      <input type="text" name="categoria" value="{{ p.categoria or pessoa.categoria or '' }}" placeholder="Categoria / tipo" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    </div>
    <textarea name="demandas" rows="2" placeholder="Demandas / correspond&#234;ncias (ex.: visita t&#233;cnica, enviar folder, convite para evento...)" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box;margin-top:8px">{{ p.demandas or pessoa.demandas or '' }}</textarea>
    <textarea name="observacao" rows="2" placeholder="Observa&#231;&#245;es" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box;margin-top:8px">{{ p.observacao or pessoa.observacao or '' }}</textarea>
    <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
      <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Salvar correspond&#234;ncia</button>
      <span style="color:#666;font-size:13px">Depois, gere as etiquetas no m&#243;dulo <a href="/impressao">Impress&#227;o</a></span>
    </div>
  </form>
</div>
"""
        idx = ficha.find("{% endblock %}")
        if idx != -1:
            ficha = ficha[:idx] + bloco + "\n" + ficha[idx:]
            gravar(ficha_p, ficha)
            print("[5/6] Ficha da pessoa ganhou a secao 'Correspondencia e Impressao'.")
        else:
            print("[5/6] Aviso: nao achei {% endblock %} na ficha - secao nao inserida.")
    else:
        print("[5/6] Ficha da pessoa ja tem a secao. Pulando.")
else:
    print("[5/6] ficha_pessoa.html nao encontrado - secao nao inserida.")

# ---------- 6) CONFIGURACAO: campos do comite (remetente) + MENU ----------
cfg_form_p = os.path.join(TPL, "configuracao_form.html")
if os.path.exists(cfg_form_p):
    cfg = ler(cfg_form_p)
    if "comite_endereco" not in cfg:
        idx = cfg.find('name="site"')
        if idx != -1:
            fim = cfg.find("\n", idx)
            extras = """
    <input type="text" name="comite_endereco" value="{{ cand.comite_endereco if cand else '' }}" placeholder="Endere&#231;o do comit&#234; (remetente)" style="flex:1;min-width:220px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="comite_telefone" value="{{ cand.comite_telefone if cand else '' }}" placeholder="Telefone do comit&#234; (remetente)" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
"""
            cfg = cfg[:fim+1] + extras + cfg[fim+1:]
            gravar(cfg_form_p, cfg)
            print("[6/6] Campos do comite adicionados ao formulario do candidato.")
        else:
            print("[6/6] Aviso: nao achei o campo site no formulario.")
    else:
        print("[6/6] Formulario do candidato ja tem os campos do comite.")

cfg_p = os.path.join(TPL, "configuracao.html")
if os.path.exists(cfg_p):
    cfg = ler(cfg_p)
    if "comite_endereco" not in cfg:
        cfg = cfg.replace("('Site', cand.site)]",
                          "('Site', cand.site), ('Endere&#231;o do comit&#234;', cand.comite_endereco), ('Telefone do comit&#234;', cand.comite_telefone)]")
        gravar(cfg_p, cfg)
        print("[6/6] Tela de configuracao exibe os dados do comite.")
    else:
        print("[6/6] Tela de configuracao ja exibe os dados do comite.")

base_p = os.path.join(TPL, "base.html")
if os.path.exists(base_p):
    base_txt = ler(base_p)
    if "/impressao" in base_txt:
        print("[6/6] Menu Impressao ja presente.")
    else:
        idx = base_txt.find('<a href="/configuracao"')
        if idx == -1:
            idx = base_txt.find('<a href="/pessoas"')
        if idx != -1:
            fim = base_txt.find("\n", idx)
            if fim != -1:
                base_txt = base_txt[:fim] + ' <a href="/impressao" class="{{ \'ativo\' if request.path.startswith(\'/impressao\') else \'\' }}">Impress&#227;o</a>' + base_txt[fim:]
                gravar(base_p, base_txt)
                print("[6/6] Menu Impressao adicionado.")
            else:
                print("[6/6] Nao consegui inserir o menu.")
        else:
            print("[6/6] Nao achei o menu - acesse pela URL /impressao.")

# ---------- VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor (pare o python app.py atual e rode de novo) e acesse /impressao.")