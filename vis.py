"""import json
import networkx as nx
import matplotlib.pyplot as plt

# ===== LOAD JSON =====
with open("7.json", "r") as f:
    data = json.load(f)

# ===== CREATE GRAPH =====
G = nx.DiGraph()

# ===== ADD NODES =====
for node in data["nodes"]:
    node_id = node["id"]

    # Shorten code for readability
    code = node["code"].split("<SEP>")[0].strip()
    code = code[:30] + "..." if len(code) > 30 else code

    label = f"{node['label'].split('|')[0]}\nL{node['line']}\n{code}"
    G.add_node(node_id, label=label)

# ===== ADD EDGES =====
edge_labels = {}
for edge in data["edges"]:
    src = edge["source"]
    tgt = edge["target"]
    etype = edge["type"]

    G.add_edge(src, tgt)
    edge_labels[(src, tgt)] = etype

# ===== LAYOUT =====
pos = nx.spring_layout(G, k=1.2, seed=42)  # adjust k for spacing

# ===== DRAW GRAPH =====
plt.figure(figsize=(12, 8))

# Nodes
nx.draw_networkx_nodes(G, pos, node_size=1500)

# Edges
nx.draw_networkx_edges(G, pos, arrows=True)

# Node labels
labels = nx.get_node_attributes(G, 'label')
nx.draw_networkx_labels(G, pos, labels, font_size=8)

# Edge labels (AST/CFG/etc.)
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

plt.title("Program Graph Visualization", fontsize=14)
plt.axis("off")
plt.tight_layout()
plt.show()
"""


"""

import json
from graphviz import Digraph

# ===== LOAD JSON =====
with open("cfg.json", "r") as f:
    data = json.load(f)

dot = Digraph(comment="Program Graph", format="svg")

dot.attr(rankdir="TB")  # Top → Bottom layout
dot.attr("node", shape="box", style="rounded,filled", color="lightblue")

# ===== ADD NODES =====
for node in data["nodes"]:
    node_id = str(node["id"])

    label_type = node["label"].split("|")[0]
    line = node["line"]

    code = node["code"].split("<SEP>")[0].strip()
    code = code[:40] + "..." if len(code) > 40 else code

    label = f"{label_type}\\nL{line}\\n{code}"

    dot.node(node_id, label)

# ===== ADD EDGES =====
for edge in data["edges"]:
    dot.edge(str(edge["source"]), str(edge["target"]), label=edge["type"])

# ===== SAVE & OPEN =====
dot.render("cfg", view=True)
"""


import json
from graphviz import Digraph

# ===== LOAD JSON =====
with open("7_enhance4.json", "r") as f:
    data = json.load(f)

dot = Digraph(format="png")

# ===== STRUCTURED LAYOUT =====
dot.attr(rankdir="LR")  # flow left → right
dot.attr(size="10,5")
dot.attr(dpi="300")
dot.attr(nodesep="0.5", ranksep="0.7")

# ===== NODE STYLE =====
dot.attr("node",
         shape="box",
         style="rounded,filled",
         color="lightblue",
         fontsize="10")

# ===== GROUP BY LINE (KEY FIX) =====
from collections import defaultdict
layers = defaultdict(list)

for node in data["nodes"]:
    layers[node["line"]].append(node)

# ===== ADD NODES LAYER-WISE =====
for line in sorted(layers.keys()):
    with dot.subgraph() as s:
        s.attr(rank="same")  # same horizontal level

        for node in layers[line]:
            node_id = str(node["id"])

            label = f"{node['label']}\nL{node['line']}"
            s.node(node_id, label)

# ===== ADD EDGES =====
for edge in data["edges"]:
    dot.edge(
        str(edge["source"]),
        str(edge["target"]),
        arrowsize="0.6"
    )

# ===== RENDER =====
dot.render("seven-aug-e4", cleanup=True)