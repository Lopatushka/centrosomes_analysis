import pandas as pd
import numpy as np
import os
from scipy.stats import mannwhitneyu

def load_data(dir, pixel_size=1):
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