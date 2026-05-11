"""import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

graph_data = {
    "nodes": [
        {"id": 25769803777,  "label": "BLOCK",      "code": "{ ... }",              "line": 10},
        {"id": 30064771077,  "label": "CALL",       "code": "buf[1024]",            "line": 11},
        {"id": 30064771079,  "label": "CALL",       "code": "fgets(buf,sizeof(buf),stdin)", "line": 12},
        {"id": 30064771081,  "label": "CALL",       "code": "target(0)",            "line": 13},
        {"id": 141733920769, "label": "RETURN",     "code": "return 0;",            "line": 14},
        {"id": 68719476743,  "label": "IDENTIFIER", "code": "buf",                  "line": 11},
        {"id": 30064771078,  "label": "CALL",       "code": "buf[1024]",            "line": 11},
        {"id": 68719476745,  "label": "IDENTIFIER", "code": "buf",                  "line": 12},
        {"id": 30064771080,  "label": "CALL",       "code": "sizeof(buf)",          "line": 12},
        {"id": 68719476747,  "label": "IDENTIFIER", "code": "stdin",                "line": 12},
        {"id": 90194313220,  "label": "LITERAL",    "code": "0",                    "line": 13},
        {"id": 90194313221,  "label": "LITERAL",    "code": "0",                    "line": 14},
        {"id": 68719476744,  "label": "IDENTIFIER", "code": "char[1024]",          "line": 11},
        {"id": 90194313219,  "label": "LITERAL",    "code": "1024",                "line": 11},
        {"id": 68719476746,  "label": "IDENTIFIER", "code": "buf",                  "line": 12},
    ],
    "edges": [
        (30064771077, 68719476745), (30064771079, 90194313220),
        (30064771081, 90194313221), (68719476743, 68719476744),
        (30064771078, 30064771077), (68719476745, 68719476746),
        (30064771080, 68719476747), (68719476747, 30064771079),
        (90194313220, 30064771081), (90194313221, 141733920769),
        (68719476744, 90194313219), (90194313219, 30064771078),
        (68719476746, 30064771080),
    ]
}

# ── Build graph ──────────────────────────────────────────────────────────────
G = nx.DiGraph()

node_meta = {n["id"]: n for n in graph_data["nodes"]}
for n in graph_data["nodes"]:
    G.add_node(n["id"], label=n["label"], code=n["code"], line=n["line"])
for src, tgt in graph_data["edges"]:
    G.add_edge(src, tgt)

# ── Color map by label ───────────────────────────────────────────────────────
COLOR_MAP = {
    "BLOCK":      "#5DCAA5",   # teal
    "CALL":       "#85B7EB",   # blue
    "IDENTIFIER": "#AFA9EC",   # purple
    "LITERAL":    "#FAC775",   # amber
    "RETURN":     "#F0997B",   # coral
}
node_colors = [COLOR_MAP.get(G.nodes[n]["label"], "#ccc") for n in G.nodes]

# ── Node labels: "LABEL\ncode (line N)" ──────────────────────────────────────
labels = {
    n: f"{G.nodes[n]['label']}\n{G.nodes[n]['code'][:16]}\nline {G.nodes[n]['line']}"
    for n in G.nodes
}

# ── Layout ───────────────────────────────────────────────────────────────────
pos = nx.spring_layout(G, seed=42, k=4)
# Fallback if pygraphviz not installed:
# pos = nx.spring_layout(G, seed=42, k=2.5)

# ── Draw ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 10))
ax.set_facecolor("#FAFAF9")
fig.patch.set_facecolor("#FAFAF9")

nx.draw_networkx_nodes(
    G, pos, ax=ax,
    node_color=node_colors,
    node_size=3600,        # slightly bigger
    linewidths=1.5,
    edgecolors="#555"
)

nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
    font_size=7, font_family="monospace")

nx.draw_networkx_edges(
    G, pos, ax=ax,
    edge_color="#333333",
    arrows=True,
    arrowstyle="-|>",
    arrowsize=25,      # bigger arrows
    width=2,           # thicker edges
    connectionstyle="arc3,rad=0.12"  # curve edges (avoids overlap)
)

# ── Legend ───────────────────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color=c, label=lbl)
    for lbl, c in COLOR_MAP.items()
]
ax.legend(handles=legend_patches, loc="upper right",
         fontsize=9, framealpha=0.9)

ax.set_title("CFG — main()", fontsize=14, fontweight="bold", pad=12)
ax.axis("off")
plt.tight_layout()
plt.savefig("cfg1.png", dpi=180, bbox_inches="tight")
plt.show()



import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

graph_data = {
    "nodes": [
        {"id": 25769803777,  "label": "BLOCK",      "code": "{ ... }",              "line": 10},
        {"id": 30064771077,  "label": "CALL",       "code": "buf[1024]",            "line": 11},
        {"id": 30064771079,  "label": "CALL",       "code": "fgets(buf,sizeof(buf),stdin)", "line": 12},
        {"id": 30064771081,  "label": "CALL",       "code": "target(0)",            "line": 13},
        {"id": 141733920769, "label": "RETURN",     "code": "return 0;",            "line": 14},
        {"id": 68719476743,  "label": "IDENTIFIER", "code": "buf",                  "line": 11},
        {"id": 30064771078,  "label": "CALL",       "code": "buf[1024]",            "line": 11},
        {"id": 68719476745,  "label": "IDENTIFIER", "code": "buf",                  "line": 12},
        {"id": 30064771080,  "label": "CALL",       "code": "sizeof(buf)",          "line": 12},
        {"id": 68719476747,  "label": "IDENTIFIER", "code": "stdin",                "line": 12},
        {"id": 90194313220,  "label": "LITERAL",    "code": "0",                    "line": 13},
        {"id": 90194313221,  "label": "LITERAL",    "code": "0",                    "line": 14},
        {"id": 68719476744,  "label": "IDENTIFIER", "code": "char[1024]",           "line": 11},
        {"id": 90194313219,  "label": "LITERAL",    "code": "1024",                 "line": 11},
        {"id": 68719476746,  "label": "IDENTIFIER", "code": "buf",                  "line": 12},
    ],
    "edges": [
        (30064771077,124554051585),(30064771079,124554051585),
        (30064771081,124554051585),(141733920769,124554051585),
        (68719476743,30064771077),(68719476743,68719476745),
        (30064771078,68719476743),(30064771078,30064771077),
        (30064771078,124554051585),(68719476745,30064771080),
        (68719476745,68719476747),(68719476745,30064771079),
        (68719476745,124554051585),(68719476747,68719476745),
        (68719476747,30064771080),(68719476747,30064771079),
        (68719476747,124554051585),(90194313220,30064771081),
        (90194313221,141733920769),(68719476744,30064771078),
        (68719476744,124554051585),(90194313219,30064771078)
    ]
}

# ── Build graph ──
G = nx.DiGraph()

for n in graph_data["nodes"]:
    G.add_node(n["id"], label=n["label"], code=n["code"], line=n["line"])

for src, tgt in graph_data["edges"]:
    G.add_edge(src, tgt)

# ── Color map ──
COLOR_MAP = {
    "BLOCK":      "#5DCAA5",
    "CALL":       "#85B7EB",
    "IDENTIFIER": "#AFA9EC",
    "LITERAL":    "#FAC775",
    "RETURN":     "#F0997B",
}

node_colors = [COLOR_MAP.get(G.nodes[n].get("label", "UNKNOWN"), "#ccc") for n in G.nodes]

# ── Labels ──
labels = {
    n: f"{G.nodes[n].get('label','UNKNOWN')}\n"
       f"{str(G.nodes[n].get('code',''))[:16]}\n"
       f"line {G.nodes[n].get('line','')}"
    for n in G.nodes
}

# ── Layout ──
pos = nx.spring_layout(G, seed=42, k=4)

# ── Draw ──
fig, ax = plt.subplots(figsize=(14, 18))
ax.set_facecolor("#FAFAF9")
fig.patch.set_facecolor("#FAFAF9")

nx.draw_networkx_nodes(G, pos, ax=ax,
    node_color=node_colors, node_size=3200,
    linewidths=1.2, edgecolors="#888")

nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
    font_size=7, font_family="monospace")

nx.draw_networkx_edges(G, pos, ax=ax,
    edge_color="#AA0000", arrows=True,
    arrowstyle="-|>", arrowsize=18,
    width=1.2, connectionstyle="arc3,rad=0.12")

# ── Legend ──
legend_patches = [
    mpatches.Patch(color=c, label=lbl)
    for lbl, c in COLOR_MAP.items()
]
ax.legend(handles=legend_patches, loc="upper right",
         fontsize=9, framealpha=0.9)

ax.set_title("PDG — main()", fontsize=14, fontweight="bold", pad=12)
ax.axis("off")

plt.tight_layout()
plt.savefig("pdg1.png", dpi=180, bbox_inches="tight")
plt.show()"""



import json
from graphviz import Digraph
from collections import defaultdict
import textwrap

# ===== LOAD JSON =====
with open("7.json", "r") as f:
    data = json.load(f)

dot = Digraph(format="svg")

# ===== LAYOUT (KEY FIXES) =====
dot.attr(
    rankdir="TB",          # TOP → BOTTOM (better readability than LR for large graphs)
    size="5,10",          # MUCH bigger canvas
    dpi="300",
    nodesep="1.0",         # more horizontal spacing
    ranksep="1.5",         # more vertical spacing
)

# ===== NODE STYLE (BIGGER TEXT) =====
dot.attr(
    "node",
    shape="box",
    style="rounded,filled",
    color="lightblue",
    fontsize="16",         # BIGGER TEXT
    width="2.5",           # wider nodes
    height="0.8"
)

# ===== GROUP BY LINE =====
layers = defaultdict(list)
for node in data["nodes"]:
    layers[node["line"]].append(node)

# ===== TEXT WRAPPING FUNCTION =====
def wrap_text(text, width=20):
    return "\n".join(textwrap.wrap(text, width))

# ===== ADD NODES =====
for line in sorted(layers.keys()):
    with dot.subgraph() as s:
        s.attr(rank="same")

        for node in layers[line]:
            node_id = str(node["id"])

            # Wrap long labels (IMPORTANT)
            label = f"{wrap_text(node['label'], 18)}\n(L{node['line']})"

            s.node(node_id, label)

# ===== EDGES =====
for edge in data["edges"]:
    dot.edge(
        str(edge["source"]),
        str(edge["target"]),
        arrowsize="0.8",
        penwidth="1.2"
    )

# ===== OUTPUT =====
dot.render("7-ori", cleanup=True)