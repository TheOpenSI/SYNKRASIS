<div align="center">
  <img src="https://github.com/Adnan525/synkrasis/blob/master/SYNKRASIS.png" alt="SYNKRASIS" width="300"/>
</div>

# Synkrasis/PyCapsule - Experiment Report on HumanEval

This report details the outcomes of experiments conducted on HumanEval with and without the custom error handling.
## 1. Success Rate (Without Custom Error Handling)

| Status | Count | Percentage |
|--------|-------|------------|
| Pass   | 129   | 78.659%    |
| Fail   | 35    | 21.341%    |

### Fix Mode Attempt Count Distribution for Passed Status

| Fix Mode Attempt Count | Count | Percentage |
|------------------------|-------|------------|
| 0                      | 115   | 89.147%    |
| 1                      | 6     | 4.651%     |
| 2                      | 4     | 3.101%     |
| 3                      | 2     | 1.550%     |
| 4                      | 1     | 0.775%     |
| 5                      | 1     | 0.775%     |

## 2. Success Rate (With Custom Error Handling)

| Status | Count | Percentage |
|--------|-------|------------|
| Pass   | 136   | 82.927%    |
| Fail   | 28    | 17.073%    |

### Fix Mode Attempt Count Distribution for Passed Status

| Fix Mode Attempt Count | Count | Percentage |
|------------------------|-------|------------|
| 0                      | 119   | 87.500%    |
| 1                      | 11    | 8.088%     |
| 4                      | 3     | 2.206%     |
| 2                      | 2     | 1.471%     |
| 5                      | 1     | 0.735%     |

## 3. Comparison with AgentCoder

The results of our experiments can be compared to the performance of other models, including **AgentCoder** (based on GPT-3.5-turbo), which showed strong performance across various datasets.

| Models                    | HumanEval     | HumanEval-ET | MBPP     | MBPP-ET | Mean  |
|----------------------------|---------------|--------------|----------|---------|-------|
| GPT-3.5-turbo | 57.3 | 42.7 | 52.2 | 36.8 | 47.3 |
| AgentCoder (GPT-3.5-turbo)  | 79.9  | 77.4 | 89.9 | 89.1 | 84.1 |
  
**GPT-4 Technical Report** from OpenAI
| Dataset | GPT-4 | GPT-3.5 | LM SOTA | SOTA |
|---------|-------|---------|---------|------|
| HumanEval | 67.0% | 48.1% | 26.2% | 65.8% |

## 4. Reference
For AgenCoder's prompt engineering, refer to the paper page 19:  
**AgentCoder: Multi-Agent-based Code Generation with Iterative Testing and Optimisation**  
Dong Huang, Jie M. Zhang, Michael Luck, Qingwen Bu, Yuhao QING, Heming Cui   
[arXiv:2312.13010v3](https://arxiv.org/pdf/2312.13010v3)
  
**GPT-4 Technical Report**  
OpenAI  
[arxiv:2303.08774](https://arxiv.org/abs/2303.08774)
