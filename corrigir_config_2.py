# -*- coding: utf-8 -*-
# Corrige a CONFIGURACAO: insere campos do comite na lista, mascaras (CNPJ/CPF/CEP/tel), busca de endereco por CEP (ViaCEP) e remetente das etiquetas.
import os, sqlite3, sys, time, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, "app.py")
DB = os.path.join(BASE, "sistema.db")
TPL = os.path.join(BASE, "templates")
CFG = os.path.join(TPL, "configuracao.html")
CFG_FORM = os.path.join(TPL, "configuracao_form.html")
ETQ = os.path.join(TPL, "impressao_etiquetas_kits.html")

def ler(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()
def gravar(p, txt):
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)

# ---------- 0) BACKUP ----------
ts = time.strftime("%Y%m%d_%H%M%S")
for p in (APP, CFG, CFG_FORM, ETQ):
    if os.path.exists(p):
        shutil.copy(p, p + ".bak_" + ts)
print("[0/5] Backup criado: *.bak_" + ts)

# ---------- 1) COLUNAS DO COMITE NO BANCO ----------
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("PRAGMA table_info(candidato)")
    cols = [r[1] for r in cur.fetchall()]
except Exception:
    cols = []
for nome, tipo in (("comite_cep","TEXT DEFAULT ''"),("comite_numero","TEXT DEFAULT ''"),
                   ("comite_bairro","TEXT DEFAULT ''"),("comite_cidade","TEXT DEFAULT ''"),
                   ("comite_uf","TEXT DEFAULT ''")):
    if nome not in cols:
        cur.execute("ALTER TABLE candidato ADD COLUMN " + nome + " " + tipo)
conn.commit(); conn.close()
print("[1/5] Colunas do comite garantidas no banco.")

# ---------- 2) INSERE OS CAMPOS DO COMITE NA LISTA CAMPOS_CANDIDATO ----------
app_txt = ler(APP)
i = app_txt.find("CAMPOS_CANDIDATO = [")
if i == -1:
    print("[!] Nao achei 'CAMPOS_CANDIDATO = [' no app.py. Nada foi gravado.")
    raise SystemExit
j = app_txt.find("]", i)
if j == -1 or j - i > 2000:
    print("[!] Nao achei o fechamento da lista. Nada foi gravado.")
    raise SystemExit
trecho_lista = app_txt[i:j]
if "comite_endereco" in trecho_lista:
    print("[2/5] Campos do comite ja estao na lista. Pulando.")
else:
    inserir = "\n    \"comite_endereco\",\"comite_telefone\",\"comite_cep\",\"comite_numero\",\"comite_bairro\",\"comite_cidade\",\"comite_uf\","
    app_txt = app_txt[:j] + inserir + app_txt[j:]
gravar(APP, app_txt)
print("[2/5] Campos do comite inseridos na lista CAMPOS_CANDIDATO.")

# ---------- 3) FORMULARIO com mascaras + busca por CEP ----------
os.makedirs(TPL, exist_ok=True)
gravar(CFG_FORM, """{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>{{ 'Editar candidato' if cand else 'Novo candidato' }}</h1>
<p style="color:#666">CNPJ, CPF, CEP e telefones têm m&#225;scara autom&#225;tica. No comit&#234;, digite o CEP e clique <b>Buscar CEP</b>: ele carrega tudo, como no cadastro de pessoas.</p>
<form method="post" action="{{ '/configuracao/' ~ cand.id ~ '/editar' if cand else '/configuracao/novo' }}" style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0" autocomplete="off">

  <h3 style="margin:0 0 10px 0">Dados do candidato</h3>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="nome_completo" value="{{ cand.nome_completo or '' }}" placeholder="Nome completo" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="nome_urna" value="{{ cand.nome_urna or '' }}" placeholder="Nome de urna (ex: CARLISE 2233)" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="cnpj" data-mask="cnpj" value="{{ cand.cnpj or '' }}" placeholder="CNPJ" style="flex:1;min-width:170px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="cpf" data-mask="cpf" value="{{ cand.cpf or '' }}" placeholder="CPF" style="flex:1;min-width:150px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="numero_candidatura" value="{{ cand.numero_candidatura or '' }}" placeholder="N&#186; candidatura" style="flex:1;min-width:140px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="cargo" value="{{ cand.cargo or '' }}" placeholder="Cargo (ex: Deputada Federal)" style="flex:1;min-width:190px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="partido" value="{{ cand.partido or '' }}" placeholder="Partido (ex: PL)" style="flex:1;min-width:140px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="sigla_partido" value="{{ cand.sigla_partido or '' }}" placeholder="Sigla" style="flex:1;min-width:90px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="coligacao" value="{{ cand.coligacao or '' }}" placeholder="Coliga&#231;&#227;o / Federa&#231;&#227;o" style="flex:1;min-width:200px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="municipio" value="{{ cand.municipio or '' }}" placeholder="Munic&#237;pio" style="flex:1;min-width:170px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="uf" value="{{ cand.uf or '' }}" placeholder="UF" maxlength="2" style="flex:1;min-width:60px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="date" name="data_nascimento" value="{{ cand.data_nascimento or '' }}" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="email" name="email" value="{{ cand.email or '' }}" placeholder="E-mail" style="flex:1;min-width:210px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="telefone" data-mask="tel" value="{{ cand.telefone or '' }}" placeholder="Telefone" style="flex:1;min-width:150px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="site" value="{{ cand.site or '' }}" placeholder="Site / redes" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>

  <h3 style="margin:16px 0 10px 0">Comit&#234; (remetente nas etiquetas)</h3>
  <p style="color:#888;font-size:12px;margin:0 0 8px 0">Digite o CEP e clique em <b>Buscar CEP</b> para preencher logradouro, bairro, cidade e UF automaticamente.</p>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;align-items:center">
    <input type="text" name="comite_cep" data-mask="cep" value="{{ cand.comite_cep or '' }}" placeholder="CEP do comit&#234;" style="flex:0 1 150px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <button type="button" onclick="buscarCep()" style="background:#0050FF;color:#fff;padding:8px 14px;border-radius:8px;border:none;cursor:pointer">Buscar CEP</button>
    <span id="cep_status" style="color:#666;font-size:12px"></span>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="comite_endereco" value="{{ cand.comite_endereco or '' }}" placeholder="Logradouro (rua/avenida)" style="flex:2;min-width:220px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="comite_numero" value="{{ cand.comite_numero or '' }}" placeholder="N&#250;mero" style="flex:0 1 100px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="comite_bairro" value="{{ cand.comite_bairro or '' }}" placeholder="Bairro" style="flex:1;min-width:150px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <input type="text" name="comite_cidade" value="{{ cand.comite_cidade or '' }}" placeholder="Cidade" style="flex:1;min-width:170px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="comite_uf" value="{{ cand.comite_uf or '' }}" placeholder="UF" maxlength="2" style="flex:0 1 60px;padding:8px;border-radius:8px;border:1px solid #ccc">
    <input type="text" name="comite_telefone" data-mask="tel" value="{{ cand.comite_telefone or '' }}" placeholder="Telefone do comit&#234;" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
  </div>

  <textarea name="biografia" rows="3" placeholder="Biografia / descri&#231;&#227;o" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box;margin-bottom:10px">{{ cand.biografia or '' }}</textarea>
  <div style="display:flex;gap:8px">
    <a href="/configuracao" style="background:#eee;color:#333;padding:8px 16px;border-radius:8px;border:1px solid #ccc;text-decoration:none">Cancelar</a>
    <button type="submit" style="background:#0050FF;color:#fff;padding:8px 20px;border-radius:8px;border:none;cursor:pointer">Salvar</button>
  </div>
</form>
</div>
<script>
function soNum(v){ return (v||'').replace(/\D/g,''); }
function mascCnpj(v){ var d=soNum(v).slice(0,14); return d.replace(/^(\d{2})(\d{3})?(\d{3})?(\d{4})?(\d{2})?$/, function(m,a,b,c,d2,e){ var r=a||''; if(b) r+='.'+b; if(c) r+='.'+c; if(d2) r+='/'+d2; if(e) r+='-'+e; return r; }); }
function mascCpf(v){ var d=soNum(v).slice(0,11); return d.replace(/^(\d{3})(\d{3})?(\d{3})?(\d{2})?$/, function(m,a,b,c,d2){ var r=a||''; if(b) r+='.'+b; if(c) r+='.'+c; if(d2) r+='-'+d2; return r; }); }
function mascCep(v){ var d=soNum(v).slice(0,8); return d.replace(/^(\d{5})(\d{3})?$/, '$1-$2'); }
function mascTel(v){ var d=soNum(v).slice(0,11); if(d.length<=10){ return d.replace(/^(\d{2})(\d{4})?(\d{4})?$/, function(m,a,b,c){ var r='('+a+')'; if(b) r+=' '+b; if(c) r+='-'+c; return r; }); } return d.replace(/^(\d{2})(\d{5})?(\d{4})?$/, function(m,a,b,c){ var r='('+a+')'; if(b) r+=' '+b; if(c) r+='-'+c; return r; }); }
function aplicar(el){ var t=el.getAttribute('data-mask'); if(!t) return; var v=el.value; if(t==='cnpj') el.value=mascCnpj(v); else if(t==='cpf') el.value=mascCpf(v); else if(t==='cep') el.value=mascCep(v); else if(t==='tel') el.value=mascTel(v); }
document.addEventListener('DOMContentLoaded', function(){
  var els=document.querySelectorAll('input[data-mask]');
  for(var i=0;i<els.length;i++){ (function(el){ el.addEventListener('input', function(){ aplicar(el); }); aplicar(el); })(els[i]); }
});
function pega(nome){ return document.querySelector('[name="'+nome+'"]'); }
function buscarCep(){
  var inp=pega('comite_cep'); var st=document.getElementById('cep_status');
  var cep=soNum(inp ? inp.value : '');
  if(cep.length!==8){ st.textContent='Digite o CEP completo (8 n\u00fameros).'; return; }
  st.textContent='Buscando...';
  fetch('https://viacep.com.br/ws/'+cep+'/json/')
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d.erro){ st.textContent='CEP n\u00e3o encontrado.'; return; }
      if(pega('comite_endereco')) pega('comite_endereco').value = d.logradouro || '';
      if(pega('comite_bairro')) pega('comite_bairro').value = d.bairro || '';
      if(pega('comite_cidade')) pega('comite_cidade').value = d.localidade || '';
      if(pega('comite_uf')) pega('comite_uf').value = (d.uf || '').toUpperCase();
      if(pega('municipio') && !pega('municipio').value) pega('municipio').value = d.localidade || '';
      if(pega('uf') && !pega('uf').value) pega('uf').value = (d.uf || '').toUpperCase();
      st.textContent='Endere\u00e7o carregado.';
      var n=pega('comite_numero'); if(n) n.focus();
    })
    .catch(function(){ st.textContent='Erro ao consultar o CEP.'; });
}
</script>
{% endblock %}
""")
print("[3/5] Formulario regravado com mascaras e busca por CEP (ViaCEP).")

# ---------- 4) TELA com caracteres reais e formatacao ----------
gravar(CFG, """{% extends "base.html" %}
{% block conteudo %}
<div style="padding:10px 0">
<h1>Configura&#231;&#227;o</h1>
<p style="color:#666">Cadastro do candidato &mdash; dados exibidos no login, dashboard, etiquetas e no sistema.</p>
{% if cand %}
<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <strong style="font-size:18px">{{ cand.nome_urna or cand.nome_completo }}</strong>
    <span style="background:#0050FF;color:#fff;border-radius:20px;padding:4px 14px">{{ cand.cargo or 'Cargo' }}</span>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-top:12px">
    {% set linhas = [('Nome completo', cand.nome_completo), ('Nome de urna', cand.nome_urna), ('CNPJ', cand.cnpj, 'cnpj'), ('CPF', cand.cpf, 'cpf'), ('Cargo', cand.cargo), ('N\u00ba candidatura', cand.numero_candidatura), ('Partido', cand.partido), ('Coliga\u00e7\u00e3o', cand.coligacao), ('Munic\u00edpio / UF', cand.municipio), ('Nascimento', cand.data_nascimento), ('E-mail', cand.email), ('Telefone', cand.telefone, 'tel'), ('Site', cand.site)] %}
    {% for linha in linhas %}
    <tr>
      <th style="text-align:left;padding:6px 8px;color:#555;width:190px">{{ linha[0] }}</th>
      <td style="padding:6px 8px">{% if linha|length > 2 and linha[2] %}<span data-format="{{ linha[2] }}">{{ linha[1] or '' }}</span>{% else %}{{ linha[1] or '-' }}{% endif %}</td>
    </tr>
    {% endfor %}
    {% if cand.biografia %}
    <tr><th style="text-align:left;padding:6px 8px;color:#555;width:190px">Biografia</th><td style="padding:6px 8px">{{ cand.biografia }}</td></tr>
    {% endif %}
    <tr><th style="text-align:left;padding:6px 8px;color:#555;width:190px">Endere&#231;o do comit&#234;</th><td style="padding:6px 8px">
      {% if cand.comite_endereco or cand.comite_numero or cand.comite_bairro or cand.comite_cidade or cand.comite_cep %}
        {{ cand.comite_endereco or '' }}{% if cand.comite_numero %}, {{ cand.comite_numero }}{% endif %}{% if cand.comite_bairro %} &middot; {{ cand.comite_bairro }}{% endif %}{% if cand.comite_cidade %} &middot; {{ cand.comite_cidade }}{% endif %}{% if cand.comite_uf %} / {{ cand.comite_uf }}{% endif %}{% if cand.comite_cep %} &middot; CEP <span data-format="cep">{{ cand.comite_cep }}</span>{% endif %}
      {% else %} - {% endif %}
    </td></tr>
    <tr><th style="text-align:left;padding:6px 8px;color:#555;width:190px">Telefone do comit&#234;</th><td style="padding:6px 8px">{% if cand.comite_telefone %}<span data-format="tel">{{ cand.comite_telefone }}</span>{% else %}-{% endif %}</td></tr>
  </table>
  <div style="margin-top:14px;display:flex;gap:8px">
    <a href="/configuracao/{{ cand.id }}/editar" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">Editar candidato</a>
    <form method="post" action="/configuracao/{{ cand.id }}/excluir" onsubmit="return confirm('Excluir este candidato?');" style="display:inline">
      <button type="submit" style="background:#eee;padding:8px 16px;border-radius:8px;border:1px solid #ccc;cursor:pointer">Excluir</button>
    </form>
  </div>
</div>
{% else %}
<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <p>Nenhum candidato cadastrado ainda.</p>
  <a href="/configuracao/novo" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">+ Cadastrar candidato</a>
</div>
{% endif %}
<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <strong>Trocar de candidato</strong>
    <a href="/configuracao/novo" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none">+ Novo candidato</a>
  </div>
  <p style="color:#666;margin-top:8px">Cadastre um novo candidato para usar o sistema com outros dados (nome, CNPJ, cargo, n&#186;). Ele vira o candidato ativo na hora.</p>
</div>
</div>
<script>
function soNum2(v){ return (v||'').replace(/\D/g,''); }
function fmtCnpj(v){ var d=soNum2(v); if(d.length!==14) return v; return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5'); }
function fmtCpf(v){ var d=soNum2(v); if(d.length!==11) return v; return d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4'); }
function fmtCep(v){ var d=soNum2(v); if(d.length!==8) return v; return d.replace(/^(\d{5})(\d{3})$/, '$1-$2'); }
function fmtTel(v){ var d=soNum2(v); if(d.length===10) return d.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3'); if(d.length===11) return d.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3'); return v; }
document.addEventListener('DOMContentLoaded', function(){
  var els=document.querySelectorAll('[data-format]');
  for(var i=0;i<els.length;i++){ var el=els[i], t=el.getAttribute('data-format'), v=el.textContent||''; var out=v;
    if(t==='cnpj') out=fmtCnpj(v); else if(t==='cpf') out=fmtCpf(v); else if(t==='cep') out=fmtCep(v); else if(t==='tel') out=fmtTel(v);
    el.textContent = out || '-';
  }
});
</script>
{% endblock %}
""")
print("[4/5] Tela de configuracao regravada (caracteres reais + formatacao).")

# ---------- 5) REMETENTE NAS ETIQUETAS DE KIT (incluir numero/bairro/cidade/UF/CEP) ----------
if os.path.exists(ETQ):
    etq = ler(ETQ)
    token = "{{ cand.comite_endereco }}"
    if token in etq:
        novo_token = ("{{ cand.comite_endereco }}{% if cand.comite_numero %}, {{ cand.comite_numero }}{% endif %}"
                      "{% if cand.comite_bairro %} &middot; {{ cand.comite_bairro }}{% endif %}"
                      "{% if cand.comite_cidade %} &middot; {{ cand.comite_cidade }}{% endif %}"
                      "{% if cand.comite_uf %} / {{ cand.comite_uf }}{% endif %}"
                      "{% if cand.comite_cep %} &middot; CEP {{ cand.comite_cep }}{% endif %}")
        etq = etq.replace(token, novo_token)
        gravar(ETQ, etq)
        print("[5/5] Remetente das etiquetas de kit agora inclui numero, bairro, cidade, UF e CEP.")
    else:
        print("[5/5] Aviso: nao achei o remetente nas etiquetas - nada alterado la.")
else:
    print("[5/5] impressao_etiquetas_kits.html nao encontrado.")

# ---------- VERIFICACAO ----------
r = subprocess.run([sys.executable, "-m", "py_compile", APP], capture_output=True, text=True)
if r.returncode == 0:
    print("[OK] app.py compila sem erros de sintaxe.")
else:
    print("[ERRO] app.py NAO compila. Cole esta saida para mim:")
    print(r.stderr)
print("\nConcluido! Reinicie o servidor e abra /configuracao -> Editar candidato.")