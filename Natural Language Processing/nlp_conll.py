# -*- coding: utf-8 -*-
"""NLP_conll.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1C2tzpFd6usy-q7r8t3KcvZRDdE-vv3Kv
"""

!pip install datasets

# Loading the dataset
from datasets import load_dataset
conll = load_dataset("conll2003")

print(conll)

print(conll["train"][0])

# Tokenizer
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

from moe_model import combinedNetwork

# Preprocessing to align labels with tokens
# Code used from the Huggingface official website
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(examples["tokens"], truncation=True, is_split_into_words=True,max_length=256,padding='max_length')

    labels = []
    for i, label in enumerate(examples[f"ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs

tokenized_dataset = conll.map(tokenize_and_align_labels,batched=True)

import numpy as np
print(len(tokenized_dataset["train"][0]["input_ids"]))

# Import the model from a seperate file
model = combinedNetwork(1,50,25,10,5)

import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader

# For padding
def collate_fn(batch):
    input_ids = [torch.tensor(sample['input_ids']) for sample in batch]
    labels = [torch.tensor(sample['labels']) for sample in batch]
    input_ids_padded = pad_sequence(input_ids, batch_first=True, padding_value=tokenizer.pad_token_id)
    labels_padded = pad_sequence(labels, batch_first=True, padding_value=-100)

    input_ids_padded = input_ids_padded.unsqueeze(2)

    return {"input_ids": input_ids_padded, "labels": labels_padded}

train_loader = DataLoader(tokenized_dataset["train"], batch_size=128, shuffle=True, collate_fn=collate_fn)

optimizer = torch.optim.Adam(model.parameters())
criterion = torch.nn.CrossEntropyLoss(ignore_index=-100)

# Training
model.train()
num_epochs = 3

for epoch in range(num_epochs):
    for batch in train_loader:
        input_ids = batch['input_ids']
        labels = batch['labels'].long()

        outputs = model(input_ids).squeeze(-1)
        #print(outputs.size())
        #print(labels.size())

        loss = criterion(outputs.transpose(1, 2), labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        print(f"Epoch [{epoch+1}/{num_epochs}], Batch loss: {loss.item()}")

test_loader = DataLoader(tokenized_dataset["test"], batch_size=128, shuffle=True, collate_fn=collate_fn)

# Testing
model.eval()
total_loss = 0
correct_predictions = 0
total_predictions = 0

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch['input_ids']
        labels = batch['labels']
        outputs = model(input_ids)

        outputs = outputs.view(-1, outputs.shape[-1])
        labels = labels.view(-1)

        loss = criterion(outputs, labels.long())
        total_loss += loss.item()
        preds = torch.argmax(outputs, dim=1)

        valid_indices = labels != -100
        valid_labels = labels[valid_indices]
        valid_preds = preds[valid_indices]

        correct_predictions += (valid_preds == valid_labels).sum().item()
        total_predictions += valid_labels.size(0)

    avg_loss = total_loss / len(test_loader)
    accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
    print(f"Test Loss: {avg_loss}")
    print(f"Test Accuracy: {accuracy}")