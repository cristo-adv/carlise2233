# -*- coding: utf-8 -*-
# Corrige o <script> sem fechamento na ficha (mata o JS) e garante a carga do Responsavel do Cadastro.
import os, time, shutil, sys

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")

# ---------- 0) BACKUP ----------
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(FICHA, FICHA + ".bak_" + ts)
print("[0/2] Backup: ficha_pessoa.html.bak_" + ts)

with open(FICHA, "r", encoding="utf-8") as f:
    txt = f.read()

# ---------- 1) INSERE O </script> FALTANTE antes do bloco do Kit ----------
marca_ini = "Carga inicial do Responsavel"
marca_kit = "Kit - Grade Categorizada"
i_ini = txt.find(marca_ini)
i_kit = txt.find(marca_kit)

if i_ini == -1 or i_kit == -1:
    print("[!] Nao localizei os marcos esperados ('%s' / '%s'). Nada foi alterado." % (marca_ini, marca_kit))
    sys.exit(0)

i_open_kit = txt.rfind("<script>", i_ini, i_kit)          # <script> que abre o bloco do Kit
i_close_entre = txt.find("</script>", i_ini, i_open_kit if i_open_kit != -1 else i_kit)

if i_close_entre == -1:
    alvo = i_open_kit if i_open_kit != -1 else i_kit
    txt = txt[:alvo] + "</script>\n" + txt[alvo:]
    print("[1/2] Inserido </script> faltante: o bloco de abas/responsavel agora fecha antes do bloco do Kit.")
else:
    print("[1/2] Ja existe fechamento entre os marcos. Nada inserido.")

# ---------- 2) BLOCO DE CARGA ISOLADO E ROBUSTO (antes de {% endblock %}) ----------
loader = """
<script>
/* ===== FIX: Responsavel do Cadastro (bloco isolado - nunca quebra as abas) ===== */
(function(){
  function carregarResp(selId, tipo, valorAtual){
    var sel = document.getElementById(selId);
    if(!sel){ return; }
    sel.innerHTML = '<option value="">CARREGANDO...</option>';
    var url = '/api/pessoas_opcoes';
    if(tipo){ url += '?tipo=' + encodeURIComponent(tipo); }
    fetch(url).then(function(r){ return r.json(); }).then(function(dados){
      var lista = dados || [];
      sel.innerHTML = '<option value="">SELECIONE</option>';
      for(var i = 0; i < lista.length; i++){
        var pp = lista[i];
        var op = document.createElement('option');
        op.value = pp.nome;
        op.textContent = pp.nome;
        sel.appendChild(op);
      }
      if(valorAtual){
        for(var k = 0; k < sel.options.length; k++){
          if(sel.options[k].value === valorAtual){ sel.selectedIndex = k; break; }
        }
      }
    }).catch(function(){
      sel.innerHTML = '<option value="">ERRO AO CARREGAR</option>';
    });
  }
  window.carregarResp = carregarResp;
  function carregarTodos(){
    var sels = document.querySelectorAll('select');
    for(var i = 0; i < sels.length; i++){
      var s = sels[i];
      if(!s.id){ continue; }
      var prim = s.options.length ? s.options[0].text : '';
      if(prim === 'CARREGANDO...'){ carregarResp(s.id, '', ''); }
    }
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', carregarTodos);
  } else {
    carregarTodos();
  }
  setTimeout(carregarTodos, 1200);
})();
</script>
"""
i_end = txt.rfind("{% endblock %}")
if i_end == -1:
    print("[!] Nao achei {% endblock %}. Nada foi alterado.")
    sys.exit(0)

txt = txt[:i_end] + "\n" + loader + "\n" + txt[i_end:]

with open(FICHA, "w", encoding="utf-8") as f:
    f.write(txt)

print("[2/2] Bloco de carga isolado adicionado (preenche selResp, selRespAutorizacao e dd_responsavel).")

# ---------- VERIFICACAO ----------
n_open = txt.count("<script>")
n_close = txt.count("</script>")
print("Balanceamento de scripts: aberturas=%d / fechamentos=%d -> %s" % (n_open, n_close, "OK" if n_open == n_close else "ATENCAO"))
print("\nConcluido! Recarregue a ficha da pessoa (Ctrl+F5).")