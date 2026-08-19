import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy.stats import mannwhitneyu

def load_data(dir):
    dfs = []
    all_dirs = []

    for root, dirs, files in os.walk(dir):
        all_dirs.append(dirs)
    
        for filename in files:
            if filename.lower().endswith(".csv"):

                path = os.path.join(root, filename)
                df = pd.read_csv(path)
                
                # If everything ended up in one column, try semicolon
                if df.shape[1] == 1:
                    df = pd.read_csv(path, sep=";")

                # Optional metadata
                df["File"] = os.path.splitext(filename)[0].replace(" ", "_")
                df["Path"] = path

                dfs.append(df) 

    # Combine all tables
    data = pd.concat(dfs, ignore_index=True)

    return data

def data_subset(df, channel):
    return df[df['Channel number']==channel]

def processing(df, threshold = 3):
    # Empty list
    results_dicts = []

    # Iteration through different samples
    for sample in df['Sample'].unique():
        sb = df[df['Sample'] == sample]
        
        # Calculate the persentage of cells with # objects >= threshold
        n_total = len(sb)
        above_thresh = sum(sb['Objects_number'] >= threshold)
        percentage = 100 * above_thresh/n_total
        sd = np.sqrt(percentage * (100  - percentage)) # SD Bernoulli? 
        
        temp = {
                'Sample_name': sample,
                'Above_threshold': above_thresh,
                'N_total_cells': n_total,
                'Percentage': percentage,
                'SD': sd,
            }
        
        results_dicts.append(temp)


    results = pd.DataFrame(results_dicts)
    
    return results

def barplot_normal(df,
                  output_dir = ".",
                  threshold = 3,
                  parameter = "centrosomes",
                  figsize=(5, 4.5),
                  bar_colors = ["#4C72B0", "#DD8452"],
                  ):
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # X positions for samples
    x = np.arange(len(df))
    
    # Bars
    ax.bar(
        x,
        df["Percentage"],
        yerr=df["SD"],
        capsize=5,
        width=0.65,
        color=bar_colors,
        edgecolor="black",
        linewidth=1.2,
        error_kw={
            "elinewidth": 1.3,
            "capthick": 1.3
        }
    )
    
    # Sample names
    ax.set_xticks(x)
    ax.set_xticklabels(df["Sample_name"])

    # Y label
    ax.set_ylabel(
        "%% Cells with %s or more %s" % (threshold, parameter),
        fontsize=13
    )
    
    # Percentage axis
    y_min = (df["Percentage"] - df["SD"]).min()
    y_max = (df["Percentage"] + df["SD"]).max()
    
    padding = (y_max - y_min) * 0.1
    
    # Add space and round up to nearest 10
    y_lower = np.floor((y_min - padding) / 10) * 10
    y_upper = np.ceil((y_max + padding) / 10) * 10
    
    y_lower = max(0, y_lower)

    ax.set_ylim(y_lower, y_upper)
    ax.set_yticks(np.arange(y_lower, y_upper + 1, 20))

    # Tick appearance
    ax.tick_params(
        axis="both",
        labelsize=11,
        width=1.2,
        length=5
    )
    
    # Clean frame
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    plt.tight_layout()
    
    plt.tight_layout()

    # Save figure
    graph_name = output_dir + "/" + parameter + ".png"
    plt.savefig(
        graph_name,
        dpi=600,
        bbox_inches="tight"
    )

    plt.show()
