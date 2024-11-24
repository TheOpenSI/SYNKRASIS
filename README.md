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
| Agent     | HumanEval gpt-4o | HumanEval gpt-4-1106-preview | HumanEval gpt-3.5-turbo-0125 | HumanEval gpt-3.5-turbo-1106 | HumanEval Qwen 2.5 7B Instruct | MBPP gpt-4o | MBPP gpt-4-1106-preview | MBPP gpt-3.5-turbo-0125 | MBPP gpt-3.5-turbo-1106 | MBPP Qwen 2.5 7B Instruct |
|---|---|---|---|---|---|---|---|---|---|---|
| MapCoder               | - | 93.9 | - | 80.5 | - | - | 83.1 | - | 78.3 | - |
| AgentCoder<sup>1</sup> | - | 96.3<sup>1</sup> | - | 79.9<sup>1</sup> | - | - | 91.8<sup>1</sup> | - | 89.1<sup>1</sup> | - |
| LATS<sup>2</sup>       | 92.7 | - | 83.8 | - | - | - | - | 81.1 | - | - |
| Qwen 2.5 Report        | - | - | - | - | 88.4 | - | - | - | - | 83.5 |
| CoSMIC(PyCapsule)      | <b>97.56</b> | <b>96.54±0.7</b> | <b>84.14±1.83</b> | <b>85.16±0.70</b> | <b>92.68</b> | <b>87.89</b> | <b>88.1</b> | 78.48±1.2 | <b>78.13±0.62</b> | 79.67 |


# Individual results
## HumanEval
### GPT-4(gpt-4o)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 97.560976 | - | - | - | - |
| Fail | 2.439024  | - | - | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 134 | 21 | 2 | 2 | - | 1 |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |


### GPT-4(gpt-4-1106-preview)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 96.95122 | 96.95122 | 95.731707 | 96.544716 | 0.70408616 |
| Fail | 3.04878 | 3.04878 | 4.268893 | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 148 | 5 | 2 | 1 | - | 3 |
| Experiment 2 | 147 | 6 | 2 | 2 | 1 | 1 |
| Experiment 3 | 142 | 7 | 5 | 2 | 1 | - |


### GPT-3.5(gpt-3.5-turbo-0125)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 85.97561 | 82.317073 | 84.146341 | 84.146341 | 1.8292685 |
| Fail | 14.02439 | 17.682927 | 15.853659 | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 112 | 15 | 8 | 1 | 2 | 3 |
| Experiment 2 | 121 | 8 | 2 | 1 | - | 3 |
| Experiment 3 | 114 | 9 | 5 | 6 | 1 | 3 |


### GPT-3.5(gpt-3.5-turbo-1106)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 84.756098 | 84.756098 | 85.97561 | 85.162602 | 0.70408558 |
| Fail | 15.243902 | 15.243902 | 14.02439 | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 113 | 13 | 5 | 3 | 3 | 2 |
| Experiment 2 | 113 | 13 | 5 | 3 | 3 | 2 |
| Experiment 3 | 116 | 14 | 6 | 1 | 3 | 1 |


### Qwen2.5 Coder Instruct
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 92.682927 | - | - | - | - |
| Fail | 7.317073  | - | - | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 118 | 27 | 5 | 2 | - | - |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |

## MBPP
### GPT-4(gpt-4o)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 87.88501 | - | - | - | - |
| Fail | 12.11499 | - | - | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 612 | 165 | 36 | 23 | 8 | 12 |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |


### GPT-4(gpt-4-1106-preview)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 88.090349 | - | - | - | - |
| Fail | 11.909651 | - | - | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 597 | 150 | 54 | 28 | 17 | 12 |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |


### GPT-3.5(gpt-3.5-turbo-0125)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 79.774127 | 78.234086 | 77.412731 | 78.473648 | 1.198787 |
| Fail | 20.225873 | 21.765914 | 22.587269 | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 580 | 115 | 44 | 17 | 12 | 9 |
| Experiment 2 | 560 | 117 | 47 | 18 | 13 | 7 |
| Experiment 3 | 535 | 231 | 116 | 51 | 26 | 15 |


### GPT-3.5(gpt-3.5-turbo-1106)
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 77.720739 | 77.823409 | 78.850103 | 78.131417 | 0.62451378 |
| Fail | 22.279261 | 22.176591 | 21.14987 | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 560 | 106 | 41 | 31 | 12 | 7 |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |


### Qwen2.5 Coder Instruct
|Status| Experiment 1 | Experiment 2 | Experiment 3 | Mean Success Rate| Sample Standard Deviation |
| --- | --- | --- | --- | --- | --- |
| Pass | 79.671458 | - | - | - | - |
| Fail | 20.328542 | - | - | - | - |

Pass Distributions-
| | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Experiment 1 | 479 | 170 | 58 | 32 | 24 | 13 |
| Experiment 2 | - | - | - | - | - | - |
| Experiment 3 | - | - | - | - | - | - |

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


