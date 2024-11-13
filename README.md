<div align="center">
  <img src="https://github.com/Adnan525/synkrasis/blob/master/SYNKRASIS.png" alt="SYNKRASIS" width="300"/>
</div>


# Synkrasis / PyCapsule - Experiment Report

This branch provides an entry point to run and analyze experiments using the PyCapsule service. PyCapsule facilitates dataset evaluation across various coding challenges and benchmarks, providing flexibility in dataset selection and sample size for efficient experimentation.

## Usage

To initiate an experiment, use the following command options. <b>If running on a shared server, ensure you specify a unique container name to prevent conflicts with other users’ sessions, as shared container environments may lead to unexpected behavior due to mounted directories.</b>

## Example usage
```bash
python main.py --datasets mbpp
``` 
  
```bash
usage: main.py [-h] [--subset-size SUBSET_SIZE] [--datasets {ds1000,humaneval,mbpp} [{ds1000,humaneval,mbpp} ...]]

Run PyCapsule experiments

optional arguments:
  -h, --help            show this help message and exit
  --subset-size SUBSET_SIZE
                        Specify the number of samples to run from each dataset. If omitted, the full dataset is used.
  --datasets {ds1000,humaneval,mbpp} [{ds1000,humaneval,mbpp} ...]
                        Choose one or more datasets for the experiment. Available options: ds1000, humaneval, mbpp.
```
<br></br>

# Final Report
|Dataset| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| HumanEval | 85.97561 | 82.317073 | 84.14634 | 84.15% | 1.829% |
| MBPP | 78.850103 | 77.5154 | 77.823409 | 78.06% | 0.699% |
  
<br></br>

# Comparison
| Agent                                      | HumanEval | MBPP  | DS1000 |
|--------------------------------------------|-----------|-------|--------|
| Mapcoder                                   | 80.5      | 78.3  | -      |
| Agentcoder                                  | 79.9      | <b>89.9</b>  | -      |
| Language Agent Tree Search (no feedback)   | 83.8      | -     | -      |
| An Empirical Study...                      | -         | -     | 35.5   |
| CoSmic                                     | <b>84.15</b>     | 78.06 | -      |

<br></br>

# HumanEval

### Pass Distribution

| Attempt | Experiment 1 | Experiment 2| Experiment 3 | Notes |
| --- | --- | --- | --- | --- |
| 0 | 112 | 121 | 114 | No Feedback |
| 1 | 15 | 8 | 9 | Feedback Loop Activated |
| 2 | 8 | 2 | 5 |  |
| 3 | 1 | 1 | 6 |  |
| 4 | 2 | 0 | 1 |  |
| 5 | 3 | 3 | 3 |  |


### Log

A detailed log of the experiment is available at: `logs/humaneval_gpt_3_5_e{exp_no}.txt`

<br></br>

# MBPP

### Pass Distribution

| Attempt | Experiment 1 | Experiment 2| Experiment 3 | Notes |
| --- | --- | --- | --- | --- |
| 0 | 563 | 560 | 560 | No Feedback |
| 1 | 114 | 126 | 122 | Feedback Loop Activated |
| 2 | 46 | 39 | 37 | |
| 3 | 21 | 15 | 23 |  |
| 4 | 7  | 10 | 9 |  |
| 5 | 17 | 5 | 7 |  |


### Log

A detailed log of the experiment is available at: `logs/mbpp_gpt_3_5_e_{exp_no}.txt`

<br></br>

# Key Settings
- OpenAI model temperature is set to 1 (default) to be able to compare with other works. [OpenAI API Reference.](https://platform.openai.com/docs/api-reference/chat/create)  
- AgenCoder used OpenAI model gpt-3.5-1160 in their experiments.
- Mapcoder used OpenAI model gpt-3.5-1160 in their experiments.
- An emperical study paper used OpenAI model gpt-3.5-1160 in their experiments.
- gpt-3.5-1106's seed seems to work. [OpenAI Community](https://community.openai.com/t/seed-param-and-reproducible-output-do-not-work/487245/5).

<br></br>

# Reference
[AgentCoder](https://arxiv.org/pdf/2312.13010v3)  
[An Empirical Study on Self-correcting Large Language Models for Data Science Code Generation](https://arxiv.org/pdf/2408.15658)  
[InverseCoder](https://arxiv.org/pdf/2407.05700)  
[Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models](https://arxiv.org/pdf/2310.04406v3)  
[MapCoder](https://arxiv.org/pdf/2405.11403)


