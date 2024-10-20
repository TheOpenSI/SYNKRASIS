<div align="center">
  <img src="https://github.com/Adnan525/synkrasis/blob/master/SYNKRASIS.png" alt="SYNKRASIS" width="300"/>
</div>


# Synkrasis/PyCapsule - Experiment Report on MBPP

This report details the outcomes of experiments conducted on the MBPP dataset.

## 1. Status Distribution

| Status | Count | Percentage |
|--------|-------|------------|
| Pass   | 722   | 74.127%    |
| Fail   | 252   | 25.873%    |

### Fix Mode Attempt Count Distribution for Passed Status

| Fix Mode Attempt Count | Count | Percentage |
|------------------------|-------|------------|
| 0                      | 565   | 78.255%    |
| 1                      | 104   | 14.404%    |
| 2                      | 26    | 3.601%     |
| 4                      | 14    | 1.939%     |
| 3                      | 12    | 1.662%     |
| 5                      | 1     | 0.139%     |

## 2. Comparison with AgentCoder

The following table shows the comparison of the results from our experiments with **AgentCoder** (based on GPT-3.5-turbo) across different datasets, including MBPP:

| Models                    | HumanEval     | HumanEval-ET | MBPP     | MBPP-ET | Mean  |
|----------------------------|---------------|--------------|----------|---------|-------|
| AgentCoder (GPT-3.5-turbo)  | 79.9 (39.4%)  | 77.4 (81.3%) | 89.9 (72.2%) | 89.1 (142.1%) | 84.1 (77.8%) |

## 3. Reference

**AgentCoder: Multi-Agent-based Code Generation with Iterative Testing and Optimisation**  
Dong Huang, Jie M. Zhang, Michael Luck, Qingwen Bu, Yuhao QING, Heming Cui  
*20 Dec 2023*  
[arXiv:2312.13010v3](https://arxiv.org/pdf/2312.13010v3)

