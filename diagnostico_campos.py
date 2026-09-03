# -*- coding: utf-8 -*-
# Mostra a lista CAMPOS_CANDIDATO e a funcao configuracao_salvar do app.py
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "app.py")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

i = txt.find("CAMPOS_CANDIDATO")
if i == -1:
    print("NAO achei CAMPOS_CANDIDATO")
else:
    print("=== CAMPOS_CANDIDATO (contexto) ===")
    print(txt[i:i+1200])
    print()

j = txt.find("def configuracao_salvar")
if j != -1:
    print("=== configuracao_salvar (inicio) ===")
    print(txt[j:j+900])
else:
    print("NAO achei configuracao_salvar")