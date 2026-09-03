# -*- coding: utf-8 -*-
# Corrige a aba IMPRESSAO na ficha da pessoa: cria a aba na barra, move para o painel p-impressao e remove o conteudo solto do final.
import os, re, time, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")

ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy(FICHA, FICHA + ".bak_" + ts)
print("[0/4] Backup: ficha_pessoa.html.bak_" + ts)

with open(FICHA, "r", encoding="utf-8") as f:
    txt = f.read()

# ---------- 1) REMOVE o bloco solto 'Correspondência e Impressão' do final ----------
i_h3 = txt.find("<h3>Correspond")
if i_h3 != -1:
    i_div = txt.rfind('<div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">', 0, i_h3)
    i_form = txt.find("</form>", i_h3)
    if i_div != -1 and i_form != -1:
        i_end = txt.find("</div>", i_form) + len("</div>")
        txt = txt[:i_div] + txt[i_end:]
        print("[1/4] Bloco solto 'Correspondência e Impressão' do final removido.")

# ---------- 2) REMOVE o bloco solto {% if aba == 'impressao' %} ... {% endif %} do final ----------
i2 = txt.find("{% if aba == 'impressao' %}")
if i2 != -1:
    j2 = txt.find("{% endif %}", i2)
    if j2 != -1:
        j2 += len("{% endif %}")
        txt = txt[:i2] + txt[j2:]
        print("[2/4] Bloco solto de impressao do final removido.")

# ---------- 3) ADICIONA a aba 'Impressão' na barra de abas (depois de Kit) ----------
if 'data-t="impressao"' in txt:
    print("[3/4] Aba Impressao ja existe na barra. Pulando.")
else:
    i_kit = txt.find('data-t="kit"')
    if i_kit != -1:
        fim_span = txt.find("</span>", i_kit)
        if fim_span != -1:
            fim_span += len("</span>")
            nova_aba = '\n  <span class="aba" data-t="impressao" onclick="ativaAba(\'impressao\')">Impress&#227;o</span>'
            txt = txt[:fim_span] + nova_aba + txt[fim_span:]
            print("[3/4] Aba 'Impression' adicionada na barra (apos Kit).")
    if 'data-t="impressao"' not in txt:
        print("[3/4] Aviso: nao achei a aba Kit - tentei antes do fim das abas.")
        i_barra = txt.find('id="barraAbas"')
        if i_barra != -1:
            i_fecha = txt.find("</div>", i_barra)
            if i_fecha != -1:
                txt = txt[:i_fecha] + '\n  <span class="aba" data-t="impressao" onclick="ativaAba(\'impressao\')">Impress&#227;o</span>' + txt[i_fecha:]
                print("[3/4] Aba 'Impressão' adicionada antes do fim da barra de abas.")

# ---------- 4) ADICIONA o PAINEL p-impressao antes de {% endblock %} ----------
if 'id="p-impressao"' in txt:
    print("[4/4] Painel p-impressao ja existe. Pulando.")
else:
    painel = '''

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
        <span style="color:#666;font-size:13px">Etiquetas de correio e envio de material ficam em <a href="/impressao">Impress&#227;o</a></span>
      </div>
    </form>
  </div>

  <div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0">
    <h3 style="margin:0 0 4px 0">Impress&#227;o do cadastro</h3>
    <p style="color:#666;font-size:13px;margin:0 0 14px 0">Escolha o que deseja imprimir desta pessoa. As p&#225;ginas abrem em formato de impress&#227;o direta.</p>
    {% if p %}
    <div style="display:flex;flex-wrap:wrap;gap:12px">
      <a href="/pessoas/{{ p.id }}/imprimir" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <div style="font-size:20px">&#128421;&#65039;</div>
        <strong style="color:#0050FF">Vis&#227;o geral do cadastro</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Ficha completa da pessoa, todos os campos, pronta para imprimir</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/contratos" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <div style="font-size:20px">&#128196;</div>
        <strong style="color:#0050FF">Contratos</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Imprime os contratos registrados desta pessoa</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/oficios" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <div style="font-size:20px">&#9993;&#65039;</div>
        <strong style="color:#0050FF">Of&#237;cios</strong>
        <div style="font-size:12px;color:#666;margin-top:4px">Imprime os of&#237;cios relacionados a esta pessoa</div>
      </a>
      <a href="/pessoas/{{ p.id }}/imprimir/recibo" style="flex:1;min-width:200px;border:1px solid #ddd;border-radius:10px;padding:14px;text-decoration:none;color:#333;background:#fafafa;display:block">
        <div style="font-size:20px">&#128203;</div>
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
    iend = txt.rfind("{% endblock %}")
    if iend != -1:
        txt = txt[:iend] + painel + "\n" + txt[iend:]
        print("[4/4] Painel p-impressao criado com Correspondencia + impressoes.")
    else:
        print("[4/4] Aviso: nao achei {% endblock %} - o painel nao foi inserido.")

with open(FICHA, "w", encoding="utf-8") as f:
    f.write(txt)

print("\nConcluido! Reinicie o servidor (pare o python app.py e rode de novo) e abra a ficha de uma pessoa.")