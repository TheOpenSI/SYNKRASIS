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

# HumanEval

### Success Rates
The overall success rates are:

|Status|Success Rate|
| --- | --- |
|Pass  |85.97561%| 
|Fail|14.02439%|


### Pass Distribution

| Attempt | Count | Notes |
| --- | --- | --- |
| 0 | 112 | No Feedback |
| 1 | 15 | Feedback Loop Activated |
| 2 | 8 |  |
| 3 | 1 |  |
| 4 | 2 |  |
| 5 | 3 |  |


## Log

A detailed log of the experiment is available at: `logs/humaneval_gpt_3_5_e1.txt`
