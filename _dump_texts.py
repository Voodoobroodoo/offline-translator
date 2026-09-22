# -*- coding: utf-8 -*-
"""Все текстовые ноды текущего экрана."""
import re

xml = open("ui.xml", encoding="utf-8").read()
nodes = re.findall(r"<node[^>]*>", xml)
print("total nodes:", len(nodes))
for node in nodes:
    text = re.search(r'text="([^"]*)"', node)
    if text and text.group(1).strip():
        bounds = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
        x1, y1, x2, y2 = map(int, bounds.groups())
        print(f"{text.group(1)[:40]:40s} -> {(x1+x2)//2},{(y1+y2)//2}")
