# -*- coding: utf-8 -*-
"""moe_model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11n-xzVyzeSt4KoZFe8nXmliqYm8lFbFI
"""

# Implementation of the LSTM, MoE and the Combined Network

import torch
import torch.nn as nn

class LSTM(nn.Module):
  def __init__(self,input_size,hidden_size):
    super().__init__()

    self.i = input_size
    self.h = hidden_size

    self.Uf = nn.Parameter(torch.Tensor(self.i,self.h))
    self.Vf = nn.Parameter(torch.Tensor(self.h,self.h))
    self.bf = nn.Parameter(torch.Tensor(self.h))
    self.Ui = nn.Parameter(torch.Tensor(self.i,self.h))
    self.Vi = nn.Parameter(torch.Tensor(self.h,self.h))
    self.bi = nn.Parameter(torch.Tensor(self.h))
    self.Uc = nn.Parameter(torch.Tensor(self.i,self.h))
    self.Vc = nn.Parameter(torch.Tensor(self.h,self.h))
    self.bc = nn.Parameter(torch.Tensor(self.h))
    self.Uo = nn.Parameter(torch.Tensor(self.i,self.h))
    self.Vo = nn.Parameter(torch.Tensor(self.h,self.h))
    self.bo = nn.Parameter(torch.Tensor(self.h))

    self.init_weights()


  def init_weights(self):
      for weight in self.parameters():
          nn.init.normal_(weight, mean=0.0, std=0.1)

  def forward(self,x):
    #x_shape = x.shape[0]
    #print("Input shape:", x.size())
    batch_size, seq_size, _ = x.size()
    ht = torch.zeros(batch_size,self.h)
    ct = torch.zeros(batch_size,self.h)
    output = []

    for i in range(seq_size):
      xt = x[:,i,:]
      xt = xt.float()
      ft = torch.sigmoid(xt @ self.Uf + ht @ self.Vf + self.bf)
      ctdash = ft * ct
      it = torch.sigmoid(xt @ self.Ui + ht @ self.Vi + self.bi)
      ctplus = torch.tanh(xt @ self.Uc + ht @ self.Vc + self.bc)
      ct = ctdash + it * ctplus
      ot = torch.sigmoid(xt @ self.Uo + ht @ self.Vo + self.bo)
      ht = ot * torch.tanh(ct)
      output.append(ht.unsqueeze(0))
    output = torch.cat(output, dim=0)
    output = output.transpose(0,1).contiguous()
    return output

# Used softmax gating for now, but I was also trying out Nosiy Top-K Gating
class MoE(nn.Module):
  def __init__(self,input_size,output_size,num_experts):
    super().__init__()

    self.i = input_size
    self.o = output_size
    self.n = num_experts

    self.experts = nn.ModuleList([nn.Linear(self.i,self.o) for _ in range(num_experts)])
    self.gate_weights = nn.Parameter(torch.Tensor(self.i,self.n))

    self.init_weights()

  def init_weights(self):
      for expert in self.experts:
          nn.init.xavier_uniform_(expert.weight)
          nn.init.constant_(expert.bias, 0.0)
      nn.init.xavier_uniform_(self.gate_weights)

  def forward(self, x):
    batch_size, seq_size, num_features = x.shape
    outputs = []

    for i in range(seq_size):
        xi = x[:, i, :]
        g = nn.Softmax(dim=1)(xi @ self.gate_weights)
        expert_preds = torch.stack([expert(xi) for expert in self.experts], dim=1)
        sum = torch.sum(g.unsqueeze(-1) * expert_preds, dim=1)
        outputs.append(sum)
    outputs = torch.stack(outputs, dim=1)

    return outputs

class combinedNetwork(nn.Module):
  def __init__(self,input_size, l1_output_size,l2_output_size, output_size,num_experts):
    super().__init__()
    self.i = input_size
    self.l1 = l1_output_size
    self.l2 = l2_output_size
    self.o = output_size
    self.experts = num_experts

    self.layers = nn.Sequential(
        LSTM(self.i,self.l1),
        MoE(self.l1,self.l2,self.experts),
        LSTM(self.l2,self.o)
    )

  def forward(self,x):
    output = self.layers(x)
    return output