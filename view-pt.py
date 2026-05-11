"""import torch
import matplotlib.pyplot as plt
import numpy as np

# Path to your file
file_path = "ast_10k_embeddings/7.pt"

# Load file
data = torch.load(file_path, map_location="cpu")

print("Loaded object type:", type(data))

# Helper to save figure
def save_plot(fig, name="output.png"):
    fig.savefig(name, bbox_inches='tight', dpi=300)
    print(f"Saved visualization as {name}")

# Case 1: Tensor
if isinstance(data, torch.Tensor):
    arr = data.numpy()
    
    fig = plt.figure()

    if arr.ndim == 1:
        plt.plot(arr)
        plt.title("1D Tensor (Line Plot)")

    elif arr.ndim == 2:
        plt.imshow(arr, cmap='viridis')
        plt.colorbar()
        plt.title("2D Tensor (Heatmap)")

    elif arr.ndim == 3:
        # Try to show first channel as image
        plt.imshow(arr[0], cmap='gray')
        plt.title("3D Tensor (First Channel)")

    else:
        print("High-dimensional tensor, flattening...")
        plt.plot(arr.flatten())
        plt.title("Flattened Tensor")

    save_plot(fig)

# Case 2: Dictionary (common for model checkpoints)
elif isinstance(data, dict):
    print("Keys:", data.keys())

    # Try to visualize first tensor-like entry
    for key, value in data.items():
        if isinstance(value, torch.Tensor):
            arr = value.numpy()
            fig = plt.figure()

            if arr.ndim == 2:
                plt.imshow(arr, cmap='viridis')
                plt.title(f"{key} (Heatmap)")
                plt.colorbar()
            else:
                plt.plot(arr.flatten())
                plt.title(f"{key} (Flattened)")

            save_plot(fig, f"{key}.png")
            break

# Case 3: List
elif isinstance(data, list):
    print(f"List with {len(data)} elements")
    
    fig = plt.figure()
    plt.plot(np.array(data).flatten())
    plt.title("List Visualization")

    save_plot(fig)

else:
    print("Unsupported type for direct visualization.")

import torch
import networkx as nx
import matplotlib.pyplot as plt

data = torch.load("ast_10k_embeddings/7.pt")

# Convert to NetworkX graph
edge_index = data.edge_index.numpy()

G = nx.Graph()
for i in range(edge_index.shape[1]):
    G.add_edge(edge_index[0][i], edge_index[1][i])

plt.figure(figsize=(8, 8))
nx.draw(G, node_size=50)
plt.title("Graph Visualization")
plt.savefig("7-vis-pt.png", dpi=300)
"""
import torch
import matplotlib.pyplot as plt
import textwrap
import math

file_path = "ast_10k_embeddings/7.pt"

data = torch.load(file_path, map_location="cpu")

# Convert full object to string safely
def stringify(obj):
    try:
        return repr(obj)
    except:
        return str(obj)

text = stringify(data)

# Wrap text so it fits nicely
wrapped_lines = []
for line in text.split("\n"):
    wrapped_lines.extend(textwrap.wrap(line, width=100))

# Split into pages (so nothing is lost)
LINES_PER_PAGE = 60
pages = [
    wrapped_lines[i:i + LINES_PER_PAGE]
    for i in range(0, len(wrapped_lines), LINES_PER_PAGE)
]

print(f"Total pages: {len(pages)}")

# Save each page as an image
for idx, page in enumerate(pages):
    fig_height = len(page) * 0.3
    fig = plt.figure(figsize=(12, fig_height))

    plt.text(0, 1, "\n".join(page), fontsize=8, family='monospace', va='top')
    plt.axis('off')

    filename = f"output_page_{idx+1}.png"
    plt.savefig(filename, bbox_inches='tight', dpi=300)
    plt.close()

    print(f"Saved {filename}")