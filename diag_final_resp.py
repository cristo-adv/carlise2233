# -*- coding: utf-8 -*-
# Diagnostico final: mostra a funcao JS carregarResp e o carregamento inicial da ficha
import os

BASE = os.path.dirname(os.path.abspath(__file__))
FICHA = os.path.join(BASE, "templates", "ficha_pessoa.html")
APP = os.path.join(BASE, "app.py")

print("############ 1) FUNCAO carregarResp e chamadas (ficha_pessoa.html) ############")
with open(FICHA, encoding="utf-8") as f:
    linhas = f.readlines()
achou = False
for i, l in enumerate(linhas):
    if "carregarResp" in l:
        achou = True
        a = max(0, i-6); b = min(len(linhas), i+14)
        print("\n--- contexto da linha %d ---" % (i+1))
        for j in range(a, b):
            print("%4d: %s" % (j+1, linhas[j].rstrip()[:230]))
if not achou:
    print("(nao achei 'carregarResp' no arquivo!)")

print("\n\n############ 2) BLOCO DE SCRIPTS (abas + carregamentos) ############")
# procura o bloco de script que define ativa/abre a pagina
for i, l in enumerate(linhas):
    if "function ativa(" in l or "DOMContentLoaded" in l or "window.onload" in l:
        a = max(0, i-2); b = min(len(linhas), i+30)
        print("\n--- bloco a partir da linha %d ---" % (i+1))
        for j in range(a, b):
            print("%4d: %s" % (j+1, linhas[j].rstrip()[:230]))

print("\n\n############ 3) filtros_responsavel no app.py ############")
with open(APP, encoding="utf-8") as f:
    app_txt = f.read()
i = app_txt.find("filtros_responsavel")
if i != -1:
    print(app_txt[max(0,i-200):i+500])
else:
    print("(nao achei 'filtros_responsavel' no app.py)")