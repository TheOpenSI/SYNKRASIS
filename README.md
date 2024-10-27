<div align="center">
  <img src="https://github.com/Adnan525/synkrasis/blob/master/SYNKRASIS.png" alt="SYNKRASIS" width="300"/>
</div>


# Synkrasis/PyCapsule - Experiment Report on DS-1000

This report details the outcomes of experiments conducted on DS-1000.

## 1. Success rate

The table below shows the overall status distribution across all experiments:

| Status | Count | Percentage (%) |
|--------|-------|----------------|
| Fail   | 649   | 64.9           |
| Pass   | 351   | 35.1           |

## 2. Fix Mode Attempt Count

| Fix Mode Attempt Count | Count | Percentage (%) |
|------------------------|-------|----------------|
| 0                      | 305   | 86.895         |
| 1                      | 41    | 11.681         |
| 2                      | 3     | 0.855          |
| 3                      | 1     | 0.285          |
| 4                      | 1     | 0.285          |

## 3. Success Rate by Library

| Library      | Success Rate (%) |
|--------------|------------------|
| Matplotlib   | 57.419           |
| Numpy        | 35.000           |
| Pandas       | 34.708           |
| Pytorch      | 25.000           |
| Scipy        | 29.245           |
| Sklearn      | 12.174           |
| Tensorflow   | 48.889           |


| Library     | Pass | Fail | Pass Percentage (%) | Fail Percentage (%) |
|-------------|------|------|---------------------|---------------------|
| Matplotlib  | 89   | 66   | 57.419              | 42.581              |
| Numpy       | 77   | 143  | 35.000              | 65.000              |
| Pandas      | 101  | 190  | 34.708              | 65.292              |
| Pytorch     | 17   | 51   | 25.000              | 75.000              |
| Scipy       | 31   | 75   | 29.245              | 70.755              |
| Sklearn     | 14   | 101  | 12.174              | 87.826              |
| Tensorflow  | 22   | 23   | 48.889              | 51.111              |

## 5. Fix Mode Attempt Count Distribution for Passed Status by Library

| Fix Mode Attempt Count | Matplotlib (%) | Numpy (%) | Pandas (%) | Pytorch (%) | Scipy (%) | Sklearn (%) | Tensorflow (%) |
|------------------------|----------------|-----------|------------|-------------|-----------|--------------|----------------|
| 0                      | 65.000         | 60.000    | 59.405     | 41.176      | 52.000    | 50.000       | 57.143         |
| 1                      | 15.000         | 20.000    | 24.752     | 23.529      | 20.000    | 21.429       | 23.810         |
| 2                      | 10.000         | 10.000    | 8.910      | 17.647      | 12.000    | 14.286       | 14.286         |
| 3                      | 5.000          | 5.000     | 4.455      | 11.765      | 8.000     | 10.714       | 4.762          |
| 4                     | 5.000          | 5.000     | 2.475      | 5.882       | 8.000     | 3.571        | 0.000          |

## 6. Comparison

| Model      | SciPy (%) | PyTorch (%) | Sklearn (%) | Matplotlib (%) | Pandas (%) | Numpy (%) | TensorFlow (%) | Overall (%) |
|------------|-----------|-------------|-------------|----------------|------------|-----------|----------------|-------------|
| GPT-3.5    | 32.08     | 72.06       | 66.09       | 32.26          | 29.55      | 17.73     | 46.67          | 35.5        |
| GPT-4      | 37.74     | 83.82       | 73.04       | 35.48          | 31.62      | 19.55     | 53.33          | 39.5        |


## 7. Reference
Quoc, T. T., Ha, D. M., Thanh, T. Q., & Nguyen-Duc, A. (2023). *An Empirical Study on Self-correcting Large Language Models for Data Science Code Generation*. Retrieved from [https://arxiv.org/pdf/2408.15658](https://arxiv.org/pdf/2408.15658)
