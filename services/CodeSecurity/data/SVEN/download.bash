#!/bin/bash

wget https://huggingface.co/datasets/bstee615/sven/resolve/main/data/train-00000-of-00001-23ea0a39e451d835.parquet?download=true -O services/CodeSecurity/data/SVEN/train.parquet
wget https://huggingface.co/datasets/bstee615/sven/resolve/main/data/val-00000-of-00001-3175b48e9b496418.parquet?download=true -O services/CodeSecurity/data/SVEN/val.parquet