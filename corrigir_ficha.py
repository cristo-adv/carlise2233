# -*- coding: utf-8 -*-
# Corrige a variavel 'pessoa' -> 'p' no trecho de Correspondencia da ficha_pessoa.html
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "templates", "ficha_pessoa.html")

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

antes = txt.count("pessoa.")
trocar = [
    ("or pessoa.data_aniversario", ""),
    ("or pessoa.categoria", ""),
    ("or pessoa.demandas", ""),
    ("or pessoa.observacao", ""),
]
for a, b in trocar:
    txt = txt.replace(a, b)

with open(path, "w", encoding="utf-8") as f:
    f.write(txt)

depois = txt.count("pessoa.")
print("Ocorrencias de 'pessoa.' antes:", antes, "| depois:", depois)
print("OK - ficha_pessoa.html corrigido.")