# -*- coding: utf-8 -*-
# Reconstroi a cauda do ficha_pessoa.html: remove lixo solto e insere painel p-impressao equilibrado.
import os, time, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")

ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(FICHA, FICHA + ".bak_" + ts)
print("[0/2] Backup: ficha_pessoa.html.bak_" + ts)

with open(FICHA, "r", encoding="utf-8") as f:
    txt = f.read()

i_script = txt.rfind("</script>")
i_block = txt.rfind("{% endblock %}")

if i_script == -1 or i_block == -1 or i_block < i_script:
    print("[ERRO] Nao encontrei os marcos esperados. Nada foi alterado.")
    raise SystemExit

cabeca = txt[:i_script + len("</script>")] + "\n"

painel = '''
<!-- ===== PAINEL IMPRESSAO (correspondencia + impressao do cadastro) ===== -->
<div class="painel {{ 'ativa' if aba == 'impressao' else '' }}" id="p-impressao">

  <div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
    <h3 style="margin:0 0 4px 0">Correspond&#234;ncia da pessoa</h3>
    <p style="color:#666;font-size:13px;margin:0 0 10px 0">Dados usados nas correspond&#234;ncias do cadastro (anivers&#225;rio, categoria, demandas e observa&#231;&#245;es).</p>
    <form method="post" action="/pessoas/{{ p.id }}/correspondencia">
      <div style="display:flex;flex-wrap:wrap;gap:10px">
        <input type="date" name="data_aniversario" value="{{ p.data_aniversario or '' }}" placeholder="Data de anivers&#225;rio" style="flex:1;min-width:180px;padding:8px;border-radius:8px;border:1px solid #ccc">
        <input type="text" name="categoria" value="{{ p.categoria or '' }}" placeholder="Categoria / tipo" style="flex:1;min-width:160px;padding:8px;border-radius:8px;border:1px solid #ccc">
      </div>
      <textarea name="demandas" rows="2" placeholder="Demandas / correspond&#234;ncias (ex.: visita t&#233;cnica, enviar folder, convite para evento...)" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box;margin-top:8px">{{ p.demandas or '' }}</textarea>
      <textarea name="observacao" rows="2" placeholder="Observa&#231;&#245;es" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ccc;box-sizing:border-box;margin-top:8px">{{ p.observacao or '' }}</textarea>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
        <button type="submit" style="background:#0050FF;color:#fff;padding:8px 16px;border-radius:8px;border:none;cursor:pointer">Salvar correspond&#234;ncia</button>
        <span style="color:#666;font-size:13px">Etiquetas de correio e envio ficam em <a href="/impressao">Impress&#227;o</a></span>
      </div>
    </form>
  </div>

  <div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
    <h3 style="margin:0 0 4px 0">Impress&#227;o do cadastro</h3>
    <p style="color:#666;font-size:13px;margin:0 0 14px 0">Escolha o que deseja imprimir desta pessoa. As p&#225;ginas abrem em formato de impress&#227;o direta.</p>
    {% if p %}
    <div style="display:flex;flex-wrap:wrap;gap:12px">
      <a href="/pessoas/{{ p.id }}/imprimir" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <strong style="color:#0050FF">Vis&#227;o geral do cadastro</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Ficha completa da pessoa, todos os campos, pronta para imprimir</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/contratos" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <strong style="color:#0050FF">Contratos</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Imprime os contratos registrados desta pessoa</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/oficios" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <strong style="color:#0050FF">Of&#237;cios</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Imprime os of&#237;cios relacionados a esta pessoa</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/recibo" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <strong style="color:#0050FF">Recibo eleitoral</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Recibo de entrega de material, conforme a legisla&#231;&#227;o eleitoral</div>
      </a>
    </div>
    {% else %}
    <p style="color:#888">Salve o cadastro primeiro para liberar as impress&#245;es desta pessoa.</p>
    {% endif %}
  </div>

</div>
'''

novo = cabeca + painel + "\n{% endblock %}\n"

with open(FICHA, "w", encoding="utf-8") as f:
    f.write(novo)

# verificacao de equilibrio
print("[1/2] Cauda reconstruida (lixo solto removido, painel p-impressao inserido).")
print("[2/2] Verificacao de equilibrio:")
for tag_abre, tag_fecha in (("{% if %}", "{% endif %}"), ("{% block %}", "{% endblock %}")):
    a = novo.count("{% if ") + novo.count("{% if%}")
    b = novo.count("{% endif %}")
    print("  if/endif:", a, "==", b, "->", "OK" if a == b else "ATENCAO")
print("\nConcluido! Reinicie o servidor e abra a ficha de uma pessoa: a aba Impressao deve aparecer na barra.")