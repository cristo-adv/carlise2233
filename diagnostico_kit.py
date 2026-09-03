# -*- coding: utf-8 -*-
# Diagnostico da ABA KIT (LISTA DE SELECAO / Gerar Etiqueta / Limpar) no ficha_pessoa.html
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "templates", "ficha_pessoa.html")

with open(path, "r", encoding="utf-8") as f:
    linhas = f.readlines()

print("=== ARQUIVO: %d linhas ===\n" % len(linhas))

# 1) acha o inicio do painel p-kit
ini_kit = None
for i, l in enumerate(linhas):
    if 'id="p-kit"' in l:
        ini_kit = i
        print("Painel p-kit comeca na linha %d: %s" % (i+1, l.rstrip()[:160]))
        break
if ini_kit is None:
    print("AVISO: nao achei id=\"p-kit\"")

# 2) palavras-chave da area de selecao
keys = ["Gerar Etiqueta", "Gerar", "Limpar", "LISTA DE SELE", "Nenhum material",
        "Selecion", "material", "selecionado", "checkbox", "name=\"", "p-kit"]
print("\n=== OCORRENCIAS (com contexto) ===")
for i, l in enumerate(linhas):
    low = l.lower()
    if any(k.lower() in low for k in ["gerar etiqueta", "lista de sele", "nenhum material", "limpar", "selecion"]):
        a = max(0, i-2)
        b = min(len(linhas), i+6)
        print("---- contexto da linha %d ----" % (i+1))
        for j in range(a, b):
            print("%4d: %s" % (j+1, linhas[j].rstrip()[:200]))
        print()

# 3) mostra ate ~150 linhas do painel p-kit (se achar)
if ini_kit is not None:
    print("\n=== CONTEUDO DO PAINEL p-kit (ate 150 linhas) ===")
    for j in range(ini_kit, min(len(linhas), ini_kit+150)):
        print("%4d: %s" % (j+1, linhas[j].rstrip()[:200]))