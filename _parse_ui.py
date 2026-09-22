# -*- coding: utf-8 -*-
"""Центры кликабельных элементов из ui.xml (bounds + resource-id)."""
import re

xml = open("ui.xml", encoding="utf-8").read()
for node in re.findall(r"<node[^>]*>", xml):
    rid = re.search(r'resource-id="([^"]*)"', node)
    text = re.search(r'text="([^"]*)"', node)
    bounds = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
    clickable = 'clickable="true"' in node
    if bounds and clickable:
        name = (rid.group(1).split("/")[-1] if rid and rid.group(1) else "") or (text.group(1)[:20] if text else "")
        x1, y1, x2, y2 = map(int, bounds.groups())
        print(f"{name:28s} -> {(x1+x2)//2},{(y1+y2)//2}")
