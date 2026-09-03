# -*- coding: utf-8 -*-
# Aplica o modulo CONFIGURACAO (cadastro do candidato) no CARLISE-2233.
import os, sqlite3, sys, re, shutil, time, subprocess

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

# ---------- 0) BACKUP AUTOMATICO ----------
ts = time.strftime("%Y%m%d_%H%M%S")
for f in ["app.py", "templates/base.html", "templates/login.html"]:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        shutil.copy(p, p + ".bak_" + ts)
print("[0/5] Backup criado: *.bak_" + ts)

app_txt = ler(APP)

# ---------- 1) TABELA candidato + dados padrao ----------
conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS candidato (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT DEFAULT '',
    nome_urna TEXT DEFAULT '',
    cnpj TEXT DEFAULT '',
    cpf TEXT DEFAULT '',
    cargo TEXT DEFAULT 'Deputada Federal',
    numero_candidatura TEXT DEFAULT '',
    partido TEXT DEFAULT '',
    sigla_partido TEXT DEFAULT '',
    coligacao TEXT DEFAULT '',
    municipio TEXT DEFAULT '',
    uf TEXT DEFAULT 'PR',
    data_nascimento TEXT DEFAULT '',
    email TEXT DEFAULT '',
    telefone TEXT DEFAULT '',
    site TEXT DEFAULT '',
    biografia TEXT DEFAULT '',
    ativo INTEGER DEFAULT 1,
    data_cadastro TEXT DEFAULT (datetime('now'))
)""")
if conn.execute("SELECT COUNT(*) FROM candidato").fetchone()[0] == 0:
    conn.execute("INSERT INTO candidato (nome_completo, nome_urna, cargo, numero_candidatura, uf, ativo) VALUES (?,?,?,?,?,1)",
                 ("CARLISE", "CARLISE 2233", "Deputada Federal", "2233", "PR"))
conn.commit(); conn.close()
print("[1/5] Tabela 'candidato' criada e CARLISE 2233 cadastrada.")

# ---------- 2) PATCH app.py ----------
if "def candidato_ativo" in app_txt:
    print("[2/5] app.py ja possui o modulo Configuracao. Pulando.")
else:
    # 2a) adiciona a criacao da tabela no init_db (apos o ultimo cria)
    i = app_txt.find("def init_db")
    if i != -1:
        fim_def = app_txt.find("\ndef ", i + 10)
        if fim_def == -1:
            fim_def = len(app_txt)
        j = app_txt.rfind("cria(", i, fim_def)
        if j != -1:
            fim_linha = app_txt.find("\n", j)
            cria_cand = '''
    cria("candidato", [
        "nome_completo TEXT DEFAULT ''",
        "nome_urna TEXT DEFAULT ''",
        "cnpj TEXT DEFAULT ''",
        "cpf TEXT DEFAULT ''",
        "cargo TEXT DEFAULT 'Deputada Federal'",
        "numero_candidatura TEXT DEFAULT ''",
        "partido TEXT DEFAULT ''",
        "sigla_partido TEXT DEFAULT ''",
        "coligacao TEXT DEFAULT ''",
        "municipio TEXT DEFAULT ''",
        "uf TEXT DEFAULT 'PR'",
        "data_nascimento TEXT DEFAULT ''",
        "email TEXT DEFAULT ''",
        "telefone TEXT DEFAULT ''",
        "site TEXT DEFAULT ''",
        "biografia TEXT DEFAULT ''",
        "ativo INTEGER DEFAULT 1",
        "data_cadastro TEXT DEFAULT (datetime('now'))",
    ])'''
            app_txt = app_txt[:fim_linha+1] + cria_cand + app_txt[fim_linha+1:]
            print("[2/5] Tabela 'candidato' adicionada ao init_db.")
        else:
            print("[!] Nao achei cria( dentro do init_db - tabela ja criada pelo passo 1, seguindo.")
    else:
        print("[!] Nao achei def init_db - tabela ja criada pelo passo 1, seguindo.")

    # 2b) rotas do modulo (antes do main)
    ROTAS = '''
# ===== MODULO CONFIGURACAO (cadastro do candidato) =====
CAMPOS_CANDIDATO = [
    "nome_completo","nome_urna","cnpj","cpf","cargo","numero_candidatura",
    "partido","sigla_partido","coligacao","municipio","uf",
    "data_nascimento","email","telefone","site","biografia",
]

def candidato_ativo():
    try:
        return buscar("SELECT * FROM candidato WHERE ativo=1 ORDER BY id DESC LIMIT 1")
    except Exception:
        return None

@app.context_processor
def injeta_candidato():
    return {"cand": candidato_ativo()}

@app.route("/configuracao")
@login_obrigatorio
def configuracao():
    return render_template("configuracao.html", cand=candidato_ativo())

@app.route("/configuracao/novo", methods=["GET","POST"])
@login_obrigatorio
def configuracao_novo():
    if request.method == "POST":
        return configuracao_salvar(0)
    return render_template("configuracao_form.html", cand=None)

@app.route("/configuracao/<int:cid>/editar", methods=["GET","POST"])
@login_obrigatorio
def configuracao_editar(cid):
    cand = buscar("SELECT * FROM candidato WHERE id=%s", (cid,))
    if not cand:
        flash("Candidato nao encontrado.", "erro")
        return redirect(url_for("configuracao"))
    if request.method == "POST":
        return configuracao_salvar(cid)
    return render_template("configuracao_form.html", cand=cand)

def configuracao_salvar(cid):
    valores = {}
    for c in CAMPOS_CANDIDATO:
        v = sane(request.form.get(c) or "")
        if c in ("cnpj","cpf"):
            v = dig(v)
        elif c == "email":
            v = v.lower()
        elif c in ("cargo","partido","sigla_partido","coligacao","municipio","uf"):
            v = norm_txt(v)
        valores[c] = v
    if not (valores.get("nome_completo") or valores.get("nome_urna")):
        flash("Informe ao menos o nome do candidato.", "erro")
        return redirect(url_for("configuracao_novo"))
    params = [valores[c] for c in CAMPOS_CANDIDATO]
    if cid:
        pares = ", ".join(c + "=%s" for c in CAMPOS_CANDIDATO)
        alterar("UPDATE candidato SET " + pares + " WHERE id=%s", params + [cid])
        flash("Dados do candidato atualizados.", "ok")
        return redirect(url_for("configuracao"))
    novo_id = inserir("INSERT INTO candidato (" + ", ".join(CAMPOS_CANDIDATO) + ", ativo) VALUES (" + ", ".join(["%s"]*len(CAMPOS_CANDIDATO)) + ", 1)", params)
    if novo_id:
        alterar("UPDATE candidato SET ativo=0 WHERE id<>%s", (novo_id,))
        flash("Candidato cadastrado e agora e o ativo do sistema.", "ok")
    else:
        flash("Nao foi possivel salvar.", "erro")
    return redirect(url_for("configuracao"))

@app.route("/configuracao/<int:cid>/excluir", methods=["POST"])
@login_obrigatorio
def configuracao_excluir(cid):
    alterar("DELETE FROM candidato WHERE id=%s", (cid,))
    flash("Candidato excluido.", "ok")
    return redirect(url_for("configuracao"))
'''
    alvo = app_txt.rfind("if __name__")
    if alvo == -1:
        alvo = app_txt.rfind("app.run(")
    if alvo == -1:
        print("[!] Nao achei 'if __name__' nem 'app.run('. Nada foi escrito para nao quebrar o app.")
        raise SystemExit
    app_txt = app_txt[:alvo] + ROTAS + "\n\n" + app_txt[alvo:]
    print("[2/5] Rotas do modulo Configuracao adicionadas ao app.py.")

    # 2c) login passa o candidato
    if 'render_template("login.html")' in app_txt:
        app_txt = app_txt.replace('render_template("login.html")', 'render_template("login.html", cand=candidato_ativo())')
        print("[2/5] Login agora envia os dados do candidato.")
    else:
        print("[!] Nao achei o render do login - login nao alterado.")
    gravar(APP, app_txt)

# ---------- 3) TEMPLATES ----------
os.makedirs(TPL, exist_ok=True)
gravar(os.path.join(TPL, "configuracao.html"), '''{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Configura&#231;&#227;o</h1>
<p style="color:#666">Cadastro do candidato &#8212; dados exibidos no login, dashboard e no sistema.</p>
{% if cand %}
<div class="card" style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <strong style="font-size:18px">{{ cand.nome_urna or cand.nome_completo }}</strong>
    <span style="background:#0050FF;color:#fff;border-radius:20px;padding:4px 14px">{{ cand.cargo or 'Cargo' }}</span>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-top:12px">
    {% set linhas = [('Nome completo', cand.nome_completo), ('Nome de urna', cand.nome_urna), ('CNPJ', cand.cnpj), ('CPF', cand.cpf), ('Cargo', cand.cargo), ('N&#186; candidatura', cand.numero_candidatura), ('Partido', cand.partido), ('Coliga&#231;&#227;o', cand.coligacao), ('Munic&#237;pio / UF', cand.municipio), ('Nascimento', cand.data_nascimento), ('E-mail', cand.email), ('Telefone', cand.telefone), ('Site', cand.site)] %}
    {% for rotulo, valor in linhas %}
    <tr>
      <th style="text-align:left;padding:6px 8px;color:#555;width:190px">{{ rotulo }}</th>
      <td style="padding:6px 8px">{{ valor or '-' }}</td>
    </tr>
    {% endfor %}
    {% if cand.biografia %}
    <tr><th style="text-align:left;padding:6px 8px;color:#555;width:190px">Biografia</th><td style="padding:6px 8px">{{ cand.biografia }}</td></tr>
    {% endif %}
  </table>
  <div style="margin-top:14px;display:flex;gap:8px">
    <a href="/configuracao/{{ cand.id }}/editar" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">Editar candidato</a>
    <form method="post" action="/configuracao/{{ cand.id }}/excluir" onsubmit="return confirm('Excluir este candidato?');" style="display:inline">
      <button type="submit" style="background:#eee;padding:8px 16px;border-radius:8px;border:1px solid #ccc;cursor:pointer">Excluir</button>
    </form>
  </div>
</div>
{% else %}
<div class="card" style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <p>Nenhum candidato cadastrado ainda.</p>
  <a href="/configuracao/novo" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">+ Cadastrar candidato</a>
</div>
{% endif %}
<div class="card" style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <strong>Trocar de candidato</strong>
    <a href="/configuracao/novo" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">+ Novo candidato</a>
  </div>
  <p style="color:#666;margin-top:8px">Cadastre um novo candidato para usar o sistema com outros dados (CNPJ, nome, cargo, n&#186;). Ele vira o candidato ativo na hora.</p>
</div>
</div>
{% endblock %}
''')
gravar(os.path.join(TPL, "configuracao_form.html"), '''{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>{{ 'Editar candidato' if cand else 'Novo candidato' }}</h1>
<p style="color:#666">Preencha os dados. Eles aparecem no login, dashboard e no sistema.</p>
<form method="post" action="{{ '/configuracao/' ~ cand.id ~ '/editar' if cand else '/configuracao/novo' }}" style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="nome_completo" value="{{ cand.nome_completo if cand else '' }}" placeholder="Nome completo" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="nome_urna" value="{{ cand.nome_urna if cand else '' }}" placeholder="Nome de urna (ex: CARLISE 2233)" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="cnpj" value="{{ cand.cnpj if cand else '' }}" placeholder="CNPJ" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="cpf" value="{{ cand.cpf if cand else '' }}" placeholder="CPF" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="numero_candidatura" value="{{ cand.numero_candidatura if cand else '2233' }}" placeholder="N&#186; candidatura" style="flex:1;min-width:140px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="cargo" value="{{ cand.cargo if cand else 'Deputada Federal' }}" placeholder="Cargo" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="partido" value="{{ cand.partido if cand else '' }}" placeholder="Partido" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="sigla_partido" value="{{ cand.sigla_partido if cand else '' }}" placeholder="Sigla" style="flex:1;min-width:80px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="coligacao" value="{{ cand.coligacao if cand else '' }}" placeholder="Coliga&#231;&#227;o / Federa&#231;&#227;o" style="flex:1;min-width:220px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="municipio" value="{{ cand.municipio if cand else '' }}" placeholder="Munic&#237;pio" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="uf" value="{{ cand.uf if cand else 'PR' }}" placeholder="UF" maxlength="2" style="flex:1;min-width:60px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="date" name="data_nascimento" value="{{ cand.data_nascimento if cand else '' }}" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="email" name="email" value="{{ cand.email if cand else '' }}" placeholder="E-mail" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="telefone" value="{{ cand.telefone if cand else '' }}" placeholder="Telefone" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="site" value="{{ cand.site if cand else '' }}" placeholder="Site / redes" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <textarea name="biografia" rows="3" placeholder="Biografia / descri&#231;&#227;o" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;margin-bottom:10px">{{ cand.biografia if cand else '' }}</textarea>
  <div style="display:flex;gap:8px">
    <a href="/configuracao" style="background:#eee;color:#333;padding:8px 16px;border-radius:8px;border:1px solid #ccc;text-decoration:none">Cancelar</a>
    <button type="submit" style="background:#0050FF;color:#fff;padding:8px 20px;border-radius:8px;border:none;cursor:pointer">Salvar</button>
  </div>
</form>
</div>
{% endblock %}
''')
print("[3/5] Telas configuracao.html e configuracao_form.html criadas.")

# ---------- 4) PATCH base.html (logo + menu) ----------
base_p = os.path.join(TPL, "base.html")
if os.path.exists(base_p):
    base_txt = ler(base_p)
    if "/configuracao" in base_txt:
        print("[4/5] base.html ja possui o menu Configuracao. Pulando.")
    else:
        antigo_logo = '<div class="logo"><b>CARLISE</b> <span>2233</span></div>'
        if antigo_logo in base_txt:
            base_txt = base_txt.replace(antigo_logo, '<div class="logo"><b>{{ (cand.nome_urna or \'CARLISE\').split(\' \')[0] }}</b> <span>{{ cand.numero_candidatura or \'2233\' }}</span></div>')
            print("[4/5] Logo do base.html agora usa o candidato ativo.")
        else:
            print("[!] Nao encontrei o logo fixo no base.html - logo permanece como esta.")
        idx = base_txt.find('<a href="/pessoas"')
        if idx != -1:
            fim_li = base_txt.find("\n", idx)
            if fim_li != -1:
                base_txt = base_txt[:fim_li] + ' <a href="/configuracao" class="{{ \'ativo\' if request.path.startswith(\'/configuracao\') else \'\' }}">Configura&#231;&#227;o</a>' + base_txt[fim_li:]
                print("[4/5] Menu Configuracao adicionado ao base.html.")
            else:
                print("[!] Nao consegui inserir o menu.")
        else:
            print("[!] Nao achei o link Pessoas no base.html - menu nao alterado.")
        gravar(base_p, base_txt)
else:
    print("[!] base.html nao encontrado - pulei.")

# ---------- 5) PATCH login.html ----------
login_p = os.path.join(TPL, "login.html")
if os.path.exists(login_p):
    login_txt = ler(login_p)
    if "cand.nome_urna" in login_txt:
        print("[5/5] login.html ja atualizado.")
    elif "CARLISE 2233" in login_txt:
        login_txt = login_txt.replace("CARLISE 2233", "{{ cand.nome_urna if cand else 'CARLISE 2233' }}")
        gravar(login_p, login_txt)
        print("[5/5] login.html atualizado com o nome do candidato.")
    else:
        print("[!] login.html nao contem 'CARLISE 2233' - nao alterei.")
else:
    print("[5/5] login.html nao encontrado - nao alterei.")

# ---------- VERIFICACAO FINAL ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor (pare o python app.py atual e rode de novo) e acesse /configuracao.")