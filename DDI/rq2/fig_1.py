import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg

from services.DDI.DDI import DDI

models = ["devstral:24b", "gpt-4-1106-preview", "phi4:14b", "qwen2.5-coder"]
exp_file_paths = ["experiment_results/devstral:24b_HumanEval_results.csv",
                  "experiment_results/gpt-4-1106-preview_humaneval_results.csv",
                  "experiment_results/phi4:14b_HumanEval_results.csv",
                  "experiment_results/qwen2.5-coder_humaneval_results.csv"]

for model_name, file_path in zip(models, exp_file_paths):    
    ddi = DDI(model_name=model_name, dataset="humaneval",
                file_path=file_path,
                maximum_debugging_attempts=5,
                theta=[50, 80, 90, 95, 99])
    ddi()

img1 = mpimg.imread('ddi_results/devstral:24b_humaneval_DDI_decay_curve.png') 
img2 = mpimg.imread('ddi_results/gpt-4-1106-preview_humaneval_DDI_decay_curve.png')
img3 = mpimg.imread('ddi_results/phi4:14b_humaneval_DDI_decay_curve.png')
img4 = mpimg.imread('ddi_results/qwen2.5-coder_humaneval_DDI_decay_curve.png')

plt.figure(figsize=(12, 8))
gs1 = gridspec.GridSpec(2, 2)
gs1.update(wspace=0.025, hspace=0.05)  # set the spacing between axes

images = [img1, img2, img3, img4]
# titles = ['Devstral:24B', 'GPT-4-1106-Preview', 'Phi4:14B', 'Qwen2.5-Coder']

for i in range(4):
    ax1 = plt.subplot(gs1[i])
    ax1.imshow(images[i])
    ax1.set_xticklabels([])
    ax1.set_yticklabels([])
    ax1.set_xticks([])
    ax1.set_yticks([])
    # ax1.set_title(titles[i], fontsize=10, pad=5)
    ax1.axis('off')  # Hide the axes
    # Don't set aspect='equal' as it will distort your plots

plt.savefig("DDI/rq2/all_models.png", 
            dpi=300, 
            bbox_inches='tight', 
            edgecolor = 'none',
            facecolor='white')
# plt.show()