#!/usr/bin/env python
# encoding: utf-8
# File Name: graph_encoder.py
# Author: Jiezhong Qiu
# Create Time: 2019/12/31 18:42
# TODO:

import dgl
import torch
import torch.nn as nn
import torch.nn.functional as F
import models.mpnn as mpnn
import models.gat as gat
from dgl.nn.pytorch import Set2Set

class GraphEncoder(nn.Module):
    """
    MPNN from
    `Neural Message Passing for Quantum Chemistry <https://arxiv.org/abs/1704.01212>`__

    Parameters
    ----------
    node_input_dim : int
        Dimension of input node feature, default to be 15.
    edge_input_dim : int
        Dimension of input edge feature, default to be 15.
    output_dim : int
        Dimension of prediction, default to be 12.
    node_hidden_dim : int
        Dimension of node feature in hidden layers, default to be 64.
    edge_hidden_dim : int
        Dimension of edge feature in hidden layers, default to be 128.
    num_step_message_passing : int
        Number of message passing steps, default to be 6.
    num_step_set2set : int
        Number of set2set steps
    num_layer_set2set : int
        Number of set2set layers
    """
    def __init__(self,
                 positional_embedding_size=32,
                 max_node_freq=8,
                 max_edge_freq=8,
                 freq_embedding_size=32,
                 output_dim=32,
                 node_hidden_dim=32,
                 edge_hidden_dim=32,
                 num_layers=6,
                 num_heads=4,
                 num_step_set2set=6,
                 num_layer_set2set=3,
                 norm=False,
                 gnn_model="mpnn"):
        super(GraphEncoder, self).__init__()

        node_input_dim = positional_embedding_size + freq_embedding_size + 2
        edge_input_dim=freq_embedding_size + 1
        if gnn_model == "mpnn":
            self.gnn = mpnn.UnsupervisedMPNN(
                    output_dim=output_dim,
                    node_input_dim=node_input_dim,
                    node_hidden_dim=node_hidden_dim,
                    edge_input_dim=edge_input_dim,
                    edge_hidden_dim=edge_hidden_dim,
                    num_step_message_passing=num_layers,
                )
        elif gnn_model == "gat":
            self.gnn = gat.UnsupervisedGAT(
                    node_input_dim=node_input_dim,
                    node_hidden_dim=node_hidden_dim,
                    edge_input_dim=edge_input_dim,
                    num_layers=num_layers,
                    num_heads=num_heads,
                    )

        self.max_node_freq = max_node_freq
        self.max_edge_freq = max_edge_freq

        self.node_freq_embedding = nn.Embedding(
                num_embeddings=max_node_freq+1,
                embedding_dim=freq_embedding_size)
        self.edge_freq_embedding = nn.Embedding(
                num_embeddings=max_edge_freq+1,
                embedding_dim=freq_embedding_size)

        self.set2set = Set2Set(node_hidden_dim, num_step_set2set, num_layer_set2set)
        self.lin_readout = nn.Sequential(
                nn.Linear(2 * node_hidden_dim, node_hidden_dim),
                nn.ReLU(),
                nn.Linear(node_hidden_dim, output_dim))
        self.norm = norm
    def forward(self, g):
        """Predict molecule labels

        Parameters
        ----------
        g : DGLGraph
            Input DGLGraph for molecule(s)
        n_feat : tensor of dtype float32 and shape (B1, D1)
            Node features. B1 for number of nodes and D1 for
            the node feature size.
        e_feat : tensor of dtype float32 and shape (B2, D2)
            Edge features. B2 for number of edges and D2 for
            the edge feature size.

        Returns
        -------
        res : Predicted labels
        """

        nfreq = g.ndata['nfreq']
        n_feat = torch.cat(
                (
                    g.ndata['pos_undirected'],
                    g.ndata['pos_directed'],
                    self.node_freq_embedding(nfreq.clamp(0, self.max_node_freq)),
                    g.ndata['seed'].unsqueeze(1).float(),
                    nfreq.unsqueeze(1).float() / self.max_node_freq
                ),
                dim=-1
                )

        efreq = g.edata['efreq']
        e_feat = torch.cat(
                (
                    self.edge_freq_embedding(efreq.clamp(0, self.max_edge_freq)),
                    efreq.unsqueeze(1).float() / self.max_edge_freq
                ),
                dim=-1
                )
        x = self.gnn(g, n_feat, e_feat)
        x = self.set2set(g, x)
        x = self.lin_readout(x)
        if self.norm:
            x = F.normalize(x, p=2, dim=-1)
        return x

if __name__ == "__main__":
    model = GraphEncoder(gnn_model="mpnn")
    print(model)
    g = dgl.DGLGraph()
    g.add_nodes(3)
    g.add_edges([0, 0, 1, 2], [1, 2, 2, 1])
    g.ndata['pos_directed'] = torch.rand(3, 16)
    g.ndata['pos_undirected'] = torch.rand(3, 16)
    g.ndata['seed'] = torch.zeros(3, dtype=torch.long)
    g.ndata['nfreq'] = torch.ones(3, dtype=torch.long)
    g.edata['efreq'] = torch.ones(4, dtype=torch.long)
    y = model(g)
    print(y.shape)
    print(y)
