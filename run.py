from ij import IJ, WindowManager
from ij.gui import GenericDialog
from ij.plugin.frame import RoiManager
from ij.gui import ShapeRoi
from ij.plugin import ChannelSplitter
from ij.measure import Measurements, ResultsTable
from ij.process import ImageStatistics
from ij.gui import NonBlockingGenericDialog
from ij.gui import WaitForUserDialog
from ij.plugin.filter import Analyzer
import os
import csv
import traceback

# ---------------------------------
# HELPERS
# ---------------------------------
def clear_results_and_rois():
    IJ.run("Clear Results")
    
def close_image(imp):
    if imp is not None:
        imp.close()
           
def img_analysis(imp):
    imp_name = imp.getTitle().split(".")[0] # get image name without extension
    
    # Split channels
    channels = ChannelSplitter.split(imp)
    if len(channels) != 3:
        IJ.log("Image {} does not have 3 channels!".format(imp_name))
        return
    
    c1 = channels[0] # DAPI channel
    c2 = channels[1] # MEARGUREMENT 1
    c3 = channels[2] # MEARGUREMENT 2

        
        

# ---------------------------------
# MAIN FUNCTION
# ---------------------------------
def main():
    # Ask user about the folder with data
    input_dir = IJ.getDirectory("Choose a directory with data to analyze")
    if input_dir is None:
        return
    
    # --- Iteration ---
    n_files = 0
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            if filename.endswith(".czi"):
                n_files += 1
                
                # Open image
                path = os.path.join(root, filename)
                imp = IJ.openImage(path)
                
                if imp is None:
                    IJ.showMessage("Failed to open image:", filename)
                    continue
                
                imp.show()
                
                IJ.log("Processing image pair {}: {}".format(n_files, root))
                img_analysis(imp)
                
                # Cleanup
                clear_results_and_rois()
                close_image(imp)
    
    IJ.log("Finished processing {} files.".format(n_files))


if __name__ == "__main__":
    main()
