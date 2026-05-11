import os
import torch
import torch.nn as nn

EMBED_DIR = "ast_node_embeddings"
OUTPUT_DIR = "ast_features"

os.makedirs(OUTPUT_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



# Child-Sum Tree-LSTM

class ChildSumTreeLSTM(nn.Module):

    def __init__(self, input_dim, hidden_dim):
        super().__init__()

        self.hidden_dim = hidden_dim

        self.W_i = nn.Linear(input_dim, hidden_dim)
        self.U_i = nn.Linear(hidden_dim, hidden_dim)

        self.W_f = nn.Linear(input_dim, hidden_dim)
        self.U_f = nn.Linear(hidden_dim, hidden_dim)

        self.W_o = nn.Linear(input_dim, hidden_dim)
        self.U_o = nn.Linear(hidden_dim, hidden_dim)

        self.W_u = nn.Linear(input_dim, hidden_dim)
        self.U_u = nn.Linear(hidden_dim, hidden_dim)


    def forward(self, x, children):

        N = x.size(0)

        h = torch.zeros(N, self.hidden_dim, device=device)
        c = torch.zeros(N, self.hidden_dim, device=device)

        for node in reversed(range(N)):

            child_ids = children[node]

            if len(child_ids) == 0:
                h_sum = torch.zeros(self.hidden_dim, device=device)
            else:
                h_sum = torch.sum(h[child_ids], dim=0)

            i = torch.sigmoid(self.W_i(x[node]) + self.U_i(h_sum))
            o = torch.sigmoid(self.W_o(x[node]) + self.U_o(h_sum))
            u = torch.tanh(self.W_u(x[node]) + self.U_u(h_sum))

            if len(child_ids) == 0:

                c[node] = i * u

            else:

                f_list = []

                for k in child_ids:
                    f = torch.sigmoid(self.W_f(x[node]) + self.U_f(h[k]))
                    f_list.append(f * c[k])

                c[node] = i * u + torch.sum(torch.stack(f_list), dim=0)

            h[node] = o * torch.tanh(c[node])

        return h


# 3-Layer AST model

class ASTTreeLSTM(nn.Module):

    def __init__(self):

        super().__init__()

        self.l1 = ChildSumTreeLSTM(768, 256)
        self.l2 = ChildSumTreeLSTM(256, 256)
        self.l3 = ChildSumTreeLSTM(256, 256)


    def forward(self, x, children):

        h = self.l1(x, children)
        h = self.l2(h, children)
        h = self.l3(h, children)

        graph_vec = torch.mean(h, dim=0)

        return graph_vec


# Building children set

def build_children(edges, node_count):

    children = [[] for _ in range(node_count)]

    for e in edges:

        p = e["source"]
        c = e["target"]

        if p < node_count and c < node_count:
            children[p].append(c)

    return children


model = ASTTreeLSTM().to(device)
model.eval()

files = [f for f in os.listdir(EMBED_DIR) if f.endswith(".pt")]

print("\nTotal graphs:", len(files))


# Feature extractor

with torch.no_grad():

    for i, f in enumerate(files, 1):

        path = os.path.join(EMBED_DIR, f)

        g = torch.load(path)

        x = g["node_embeddings"].to(device)

        children = build_children(g["edges"], len(x))

        feature = model(x, children)

        output = {
            "filename": f,
            "graph_id": g["graph_id"],
            "ast_feature": feature.cpu()
        }

        out_path = os.path.join(OUTPUT_DIR, f)

        torch.save(output, out_path)

        if i % 50 == 0 or i == len(files):
            print(f"Processed {i}/{len(files)}")


print("\nAST feature extraction complete.")
print("Saved in:", OUTPUT_DIR)