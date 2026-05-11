import os
import json
import torch
from tqdm import tqdm

GRAPH_FOLDER = "augmented_graphs/train/ast"

EMBED_FOLDERS = [
    "ast_node_embeddings",
    "ast_new"
]

total_fixed = 0
missing_json = 0

for EMBED_FOLDER in EMBED_FOLDERS:

    files = [f for f in os.listdir(EMBED_FOLDER) if f.endswith(".pt")]

    print(f"\nProcessing folder: {EMBED_FOLDER}")
    print("Files:", len(files))

    for f in tqdm(files):

        idx = f.replace(".pt", "")
        pt_path = os.path.join(EMBED_FOLDER, f)
        json_path = os.path.join(GRAPH_FOLDER, f"{idx}.json")

        # -----------------------------
        # Check JSON exists
        # -----------------------------
        if not os.path.exists(json_path):
            print("Missing JSON:", idx)
            missing_json += 1
            continue

        # -----------------------------
        # Load original JSON graph
        # -----------------------------
        with open(json_path, "r", encoding="utf8") as jf:
            graph = json.load(jf)

        edges = graph.get("edges", [])
        method = graph.get("method", "")
        graph_id = graph.get("id", idx)

        # -----------------------------
        # Load embedding tensor
        # -----------------------------
        emb = torch.load(pt_path)

        # If already fixed (skip)
        if isinstance(emb, dict) and "node_embeddings" in emb:
            continue

        # -----------------------------
        # Create correct structure
        # -----------------------------
        new_data = {
            "graph_id": graph_id,
            "method": method,
            "node_embeddings": emb,
            "edges": edges
        }

        # -----------------------------
        # Overwrite file
        # -----------------------------
        torch.save(new_data, pt_path)

        total_fixed += 1

# -----------------------------
# Summary
# -----------------------------
print("\n✅ FIX COMPLETE")
print("Total fixed:", total_fixed)
print("Missing JSON:", missing_json)