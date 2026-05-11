"""import networkx as nx
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict


# ===== BUILD GRAPH =====
G = nx.DiGraph()

with open("7_enhance1.json", "r") as f:
    graph_data = json.load(f)

for n in graph_data["nodes"]:
    G.add_node(n["id"], label=n["label"], code=n["code"], line=n["line"])

for e in graph_data["edges"]:
    G.add_edge(e["source"], e["target"])

# ===== COLOR MAP =====
COLOR_MAP = {
    "BLOCK":      "#5DCAA5",
    "CALL":       "#85B7EB",
    "IDENTIFIER": "#AFA9EC",
    "LITERAL":    "#FAC775",
    "RETURN":     "#F0997B",
}

node_colors = [COLOR_MAP.get(G.nodes[n].get("label",""), "#ccc") for n in G.nodes]

# ===== LABELS =====
labels = {
    n: f"{G.nodes[n].get('label','')}\nL{G.nodes[n].get('line','')}"
    for n in G.nodes
}

# ===== TREE-LIKE LAYOUT (KEY PART) =====
layers = defaultdict(list)
for n in G.nodes:
    line = G.nodes[n].get("line", 0)
    layers[line].append(n)

pos = {}
y_gap = 3
x_gap = 3

for i, line in enumerate(sorted(layers.keys())):
    nodes = layers[line]
    width = (len(nodes)-1) * x_gap

    for j, node in enumerate(nodes):
        x = j * x_gap - width / 2   # center align
        y = -i * y_gap
        pos[node] = (x, y)

# ===== DRAW =====
fig, ax = plt.subplots(figsize=(18, 14))
ax.set_facecolor("#FAFAF9")

nx.draw_networkx_nodes(
    G, pos,
    node_color=node_colors,
    node_size=2600,
    edgecolors="#555",
    linewidths=1.2
)

nx.draw_networkx_labels(
    G, pos,
    labels=labels,
    font_size=8,
    font_family="monospace"
)

nx.draw_networkx_edges(
    G, pos,
    edge_color="#222",
    arrows=True,
    arrowstyle='-|>',      # proper arrow head
    arrowsize=35,          # BIG arrows (important)
    width=2,
    min_source_margin=25,  # move arrow away from node
    min_target_margin=25,
    connectionstyle="arc3,rad=0.0"  # STRAIGHT edges (very important)
)


# ===== GROUP EDGES BY (SOURCE, TARGET) =====
edge_groups = defaultdict(list)
for u, v in G.edges():
    edge_groups[(u, v)].append((u, v))

# ===== DRAW EDGES WITH CURVATURE =====
for (u, v), edges in edge_groups.items():
    n = len(edges)

    # distribute curvature
    if n == 1:
        rad_values = [0.0]
    else:
        spread = 0.6  # controls how far curves spread
        step = spread / (n - 1)
        rad_values = [-spread/2 + i * step for i in range(n)]

    for rad in rad_values:
        nx.draw_networkx_edges(
            G, pos,
            edgelist=[(u, v)],
            edge_color="#222",
            arrows=True,
            arrowstyle='-|>',
            arrowsize=30,
            width=1.8,
            min_source_margin=20,
            min_target_margin=20,
            connectionstyle=f"arc3,rad={rad}"
        )

# ===== LEGEND =====
legend_patches = [
    mpatches.Patch(color=c, label=lbl)
    for lbl, c in COLOR_MAP.items()
]
ax.legend(handles=legend_patches, loc="upper right", fontsize=9)



plt.tight_layout()
plt.savefig("7enh.png", dpi=200, bbox_inches="tight")
plt.show()
"""

import networkx as nx
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from networkx.drawing.nx_pydot import graphviz_layout
import textwrap
# ===== BUILD GRAPH =====
G = nx.DiGraph()

with open("7p.json", "r") as f:
    graph_data = json.load(f)

for n in graph_data["nodes"]:
    G.add_node(
        n["id"],
        label=n["label"],
        line=n["line"]
    )

for e in graph_data["edges"]:
    G.add_edge(e["source"], e["target"])

# ===== GRAPHVIZ LAYOUT (MAIN FIX) =====
#pos = graphviz_layout(G, prog="dot")  
# try: "dot" (hierarchy), "sfdp" (spread), "neato" (organic)
pos = nx.spring_layout(G, k=1.5, iterations=150)
# ===== COLOR MAP =====
COLOR_MAP = {
    "BLOCK":      "#5DCAA5",
    "CALL":       "#85B7EB",
    "IDENTIFIER": "#AFA9EC",
    "LITERAL":    "#FAC775",
    "RETURN":     "#F0997B",
}

node_colors = [
    COLOR_MAP.get(G.nodes[n].get("label", ""), "#ccc")
    for n in G.nodes
]

def wrap_label(text, width=12):
    return "\n".join(textwrap.wrap(text, width))

"""labels = {
    n: wrap_label(f"{G.nodes[n]['label']} L{G.nodes[n]['line']}", width=14)
    for n in G.nodes
}"""
labels = {
    n: wrap_label(
        f"{G.nodes[n].get('label', 'UNK')} L{G.nodes[n].get('line', '?')}",
        width=14
    )
    for n in G.nodes
}

# ===== DRAW =====
fig, ax = plt.subplots(figsize=(24, 18))  # bigger for clarity
#ax.set_facecolor("#FAFAF9")

# ===== NODES =====
nx.draw_networkx_nodes(
    G, pos,
    node_color=node_colors,
    node_size=5500,
    edgecolors="#444",
    linewidths=1.2
)

# ===== LABELS =====
nx.draw_networkx_labels(
    G, pos,
    labels=labels,
    font_size=12,              # slightly smaller
    font_family="monospace",
    verticalalignment='center',
    horizontalalignment='center'
)

# ===== EDGES (clean, slightly curved) =====
nx.draw_networkx_edges(
    G, pos,
    edge_color="#222",
    arrows=True,
    arrowstyle='-|>',
    arrowsize=40,
    width=1.8,
    connectionstyle="arc3,rad=0.08",
    min_source_margin=25,
    min_target_margin=35,
    node_size=5500    # important: tells NetworkX node radius          # ⬅️ THIS FIXES ARROW VISIBILITY
)

# ===== LEGEND =====
legend_patches = [
    mpatches.Patch(color=c, label=lbl)
    for lbl, c in COLOR_MAP.items()
]
ax.legend(handles=legend_patches, loc="upper right", fontsize=10)

ax.set_axis_off()

for spine in ax.spines.values():
    spine.set_visible(False)

fig.patch.set_edgecolor('none')
fig.patch.set_linewidth(0)

# ===== SAVE (HIGH QUALITY FOR PPT) =====
plt.tight_layout()
plt.savefig("7pdg.png", dpi=400, bbox_inches='tight', pad_inches=0)
plt.show()