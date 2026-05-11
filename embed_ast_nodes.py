"""import os
import json
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

# -----------------------------
# SETTINGS
# -----------------------------
GRAPH_FOLDER = "augmented_graphs/train/ast"
OUTPUT_FOLDER = "ast_node_embeddings"
IDX_FILE = "selected_10k_idx.txt"

DEVICE = "cpu"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------
# Load CodeBERT
# -----------------------------
print("Loading CodeBERT...")

tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")

model.to(DEVICE)
model.eval()

# -----------------------------
# Load selected idx
# -----------------------------
with open(IDX_FILE) as f:
    idx_list = [line.strip() for line in f if line.strip()]

files = [f"{idx}.json" for idx in idx_list]

print("Total requested graphs:", len(files))

# -----------------------------
# Process graphs
# -----------------------------
processed = 0
missing = 0

for file in tqdm(files):

    path = os.path.join(GRAPH_FOLDER, file)

    if not os.path.exists(path):
        print("Missing:", file)
        missing += 1
        continue

    with open(path, "r", encoding="utf8") as f:
        graph = json.load(f)

    nodes = graph["nodes"]

    node_embeddings = []

    for node in nodes:

        text = node.get("code", "")

        text = text.replace("<SEP>", " ")

        if text.strip() == "":
            node_embeddings.append(torch.zeros(768))
            continue

        tokens = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256
        )

        tokens = {k: v.to(DEVICE) for k, v in tokens.items()}

        with torch.no_grad():
            outputs = model(**tokens)

        embedding = outputs.last_hidden_state[:, 0, :].squeeze(0)

        node_embeddings.append(embedding.cpu())

    node_embeddings = torch.stack(node_embeddings)

    idx = file.replace(".json", "")
    save_path = os.path.join(OUTPUT_FOLDER, f"{idx}.pt")

    torch.save(node_embeddings, save_path)

    processed += 1

# -----------------------------
# Summary
# -----------------------------
print("\nAST node embeddings completed.")
print("Processed:", processed)
print("Missing:", missing)
"""


import os
import json
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

GRAPH_FOLDER = "augmented_graphs/train/ast"
OUTPUT_FOLDER = "ast_node_embeddings"
IDX_FILE = "selected_10k_idx.txt"

DEVICE = "cpu"

skipped_ids = []
total_seen = 0

MAX_NODES = 400
BATCH_SIZE = 32
MAX_TOKENS = 128

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load CodeBERT
print("Loading CodeBERT...")

tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")

model.to(DEVICE)
model.eval()

# Load selected idx
with open(IDX_FILE) as f:
    idx_list = [line.strip() for line in f if line.strip()]

files = [f"{idx}.json" for idx in idx_list]

print("Total requested graphs:", len(files))

# Resume support 
done_files = set(f.replace(".pt", "") for f in os.listdir(OUTPUT_FOLDER))

print("Already processed:", len(done_files))

# Process graphs
processed = 0
skipped_large = 0
missing = 0

for file in tqdm(files):

    idx = file.replace(".json", "")

    # Skip already processed
    if idx in done_files:
        continue

    path = os.path.join(GRAPH_FOLDER, file)

    if not os.path.exists(path):
        print("Missing:", file)
        missing += 1
        continue

    with open(path, "r", encoding="utf8") as f:
        graph = json.load(f)

    nodes = graph["nodes"]

    total_seen += 1  

    if len(nodes) > MAX_NODES:
        print(f"Skipping large graph {idx} (nodes={len(nodes)})")
        skipped_ids.append(idx)
        skipped_large += 1
        continue

    node_embeddings = []

    texts = []
    valid_mask = []

    # Prepare node texts
    for node in nodes:
        text = node.get("code", "").replace("<SEP>", " ").strip()

        if text == "":
            node_embeddings.append(torch.zeros(768))
            valid_mask.append(False)
        else:
            texts.append(text)
            valid_mask.append(True)

   
    # Batch embedding
    embeddings_iter = iter([])

    if len(texts) > 0:
        all_embeddings = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i + BATCH_SIZE]

            tokens = tokenizer(
                batch_texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=MAX_TOKENS
            )

            tokens = {k: v.to(DEVICE) for k, v in tokens.items()}

            with torch.no_grad():
                outputs = model(**tokens)

            batch_embeddings = outputs.last_hidden_state[:, 0, :]

            all_embeddings.append(batch_embeddings.cpu())

            del tokens, outputs, batch_embeddings

        all_embeddings = torch.cat(all_embeddings, dim=0)
        embeddings_iter = iter(all_embeddings)

    
    # Reconstruct embeddings
    final_embeddings = []

    for is_valid in valid_mask:
        if is_valid:
            final_embeddings.append(next(embeddings_iter))
        else:
            final_embeddings.append(torch.zeros(768))

    node_embeddings = torch.stack(final_embeddings)

    save_path = os.path.join(OUTPUT_FOLDER, f"{idx}.pt")
    torch.save(node_embeddings, save_path)

    processed += 1


print("\n--- SKIP ANALYSIS ---")
print("Total graphs seen:", total_seen)
print("Skipped graphs:", skipped_large)

if total_seen > 0:
    percent = (skipped_large / total_seen) * 100
    print(f"Skipped %: {percent:.2f}%")

with open("skipped_ast.txt", "w") as f:
    for i in skipped_ids:
        f.write(i + "\n")

print("\nAST node embeddings completed.")
print("Processed:", processed)
print("Skipped large:", skipped_large)
print("Missing:", missing)