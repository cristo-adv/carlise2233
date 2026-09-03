# -*- coding: utf-8 -*-
# Diagnostico da estrutura de abas do ficha_pessoa.html
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "templates", "ficha_pessoa.html")

with open(path, "r", encoding="utf-8") as f:
    linhas = f.readlines()

print("=== TAMANHO DO ARQUIVO: %d linhas ===\n" % len(linhas))

print("=== LINHAS QUE MENCIONAM aba/tab (primeiras 40) ===")
count = 0
for i, l in enumerate(linhas, 1):
    if ("aba" in l.lower()) or ("tab" in l.lower()):
        print("%4d: %s" % (i, l.rstrip()[:180]))
        count += 1
        if count >= 40:
            break
if count == 0:
    print("(nenhuma linha com aba/tab encontrada)")

print("\n=== ULTIMAS 60 LINHAS DO ARQUIVO ===")
for i, l in enumerate(linhas[-60:], len(linhas)-59):
    print("%4d: %s" % (i, l.rstrip()[:180]))