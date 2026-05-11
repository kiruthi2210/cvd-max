import os
import json
import re
from collections import defaultdict

TRAIN_JSON = "train.json"

GRAPH_ROOT = "simplified_graphs/train"
OUTPUT_ROOT = "augmented_graphs/train"

GRAPH_TYPES = ["ast", "cfg", "pdg"]

FUNC_PATTERN = re.compile(r'\bFUNC_\d+\b')
VAR_PATTERN = re.compile(r'\bVAR_\d+\b')


def load_graph(path):

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
        text = text.replace("\0", "").replace("\x00", "")

        return json.loads(text)


def save_graph(graph, path):

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f)


print("Loading dataset...")

with open(TRAIN_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Total samples:", len(data))


groups = defaultdict(list)

for item in data:

    key = (item["cwe"][0], item["project"])
    groups[key].append(item)


group_factors = {}

for key, samples in groups.items():

    vuln = sum(1 for s in samples if s["target"] == 1)
    non_vuln = sum(1 for s in samples if s["target"] == 0)

    if vuln == 0:
        continue

    factor = non_vuln // vuln

    if factor > 0:
        group_factors[key] = factor


print("Groups requiring augmentation:", len(group_factors))


dataset_map = {}

for item in data:

    dataset_map[item["idx"]] = item


def augment_code(code, i):

    code = VAR_PATTERN.sub(lambda m: f"{m.group(0)}_enhance{i}", code)
    code = FUNC_PATTERN.sub(lambda m: f"{m.group(0)}_enhance{i}", code)

    return code


def augment_graph(graph, aug_id):

    new_graph = {
        "method": graph.get("method"),
        "id": graph.get("id"),
        "nodes": [],
        "edges": graph.get("edges", [])
    }

    for node in graph["nodes"]:

        new_node = dict(node)

        new_node["code"] = augment_code(
            node.get("code", ""),
            aug_id
        )

        new_graph["nodes"].append(new_node)

    return new_graph


print("\nStarting graph augmentation...\n")

total_augmented = 0
total_processed = 0


for gtype in GRAPH_TYPES:

    input_dir = os.path.join(GRAPH_ROOT, gtype)
    output_dir = os.path.join(OUTPUT_ROOT, gtype)

    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]

    print(f"\nProcessing {gtype.upper()} graphs | {len(files)} files")

    for i,fname in enumerate(files,1):
        if i % 500 == 0:print(f"{gtype} processed {i}/{len(files)}")

        name = fname.split(".")[0]

        # skip non-numeric filenames (e.g., unknown.json)

        if not name.isdigit():continue

        idx = int(name)

        out_path = os.path.join(output_dir, fname)
        # skip already processed graphs

        if os.path.exists(out_path):continue

        graph = load_graph(os.path.join(input_dir, fname))
        save_graph(graph, os.path.join(output_dir, fname))
        sample = dataset_map.get(idx)
        if sample is None:
            continue
        if sample["target"] != 1:
            continue
    

        key = (sample["cwe"][0], sample["project"])

        factor = group_factors.get(key, 0)

        for i in range(1, factor + 1):

            aug_graph = augment_graph(graph, i)

            new_name = f"{idx}_enhance{i}.json"

            save_graph(
                aug_graph,
                os.path.join(output_dir, new_name)
            )

            total_augmented += 1

        total_processed += 1


print("\nAugmentation complete")
print("Vulnerable graphs processed:", total_processed)
print("Augmented graphs created:", total_augmented)