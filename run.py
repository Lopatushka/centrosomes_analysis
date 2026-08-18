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
def ask_params_for_image(n_slices):
    gd = NonBlockingGenericDialog("Maximum Intensity Projection Parameters")
    gd.addMessage(
        "Choose the slice range.\n"
        "Available slices: 1-%d" % n_slices
    )
    
    # Fields
    gd.addNumericField("First slice:", 1, 0)
    gd.addNumericField("Last slice:", n_slices, 0)
    gd.addCheckbox("Stop analysis", False) # bool
    
    # Show dialog
    gd.showDialog()
    
    # User pressed Cancel
    if gd.wasCanceled():
        return None
    
    # Read values in the same order they were added
    first_slice = int(gd.getNextNumber())
    last_slice = int(gd.getNextNumber())
    stop_analysis = gd.getNextBoolean()
    
    # Keep values within valid range
    first_slice = max(1, first_slice)
    last_slice = min(n_slices, last_slice)
    
    if first_slice > last_slice:
        print("Invalid slice range.")
        return None

    return {
        "first_slice": first_slice,
        "last_slice": last_slice,
        "stop_analysis": stop_analysis
    }
    
    
def clear_results_and_rois():
    IJ.run("Clear Results")
    
def close_image(imp):
    if imp is not None:
        imp.close()
        
def close_all_images():
    """
    Close all currently open images without saving.
    """
    image_ids = WindowManager.getIDList()

    if image_ids is None:
        return

    for image_id in image_ids:
        imp = WindowManager.getImage(image_id)

        if imp is not None:
            imp.changes = False  # prevent "Save changes?" dialog
            imp.close()
           
def img_analysis(imp):   
    imp_name = imp.getTitle().split(".")[0] # get image name without extension
    n_slices = imp.getNSlices()
    
    # Split channels
    channels = ChannelSplitter.split(imp)
    if len(channels) != 3:
        IJ.log("Image {} does not have 3 channels!".format(imp_name))
        return True
    
    c1 = channels[0] # DAPI channel
    c2 = channels[1] # MEARGUREMENT 1
    c3 = channels[2] # MEARGUREMENT 2
    
    # --- Changes names of splitted images ---
    c1.setTitle("DAPI_{}".format(imp_name))
    c2.setTitle("MEAS1_{}".format(imp_name))
    c3.setTitle("MEAS2_{}".format(imp_name))
    
    # Show splitted images
    c1.show()
    c2.show()
    c3.show()
    
    # Ask user about the parameters: first and last slice for the maximum intensity projection
    params = ask_params_for_image(n_slices)
    if params["stop_analysis"]:
        return False
    
    first_slice = params["first_slice"] if params is not None else 1
    last_slice = params["last_slice"] if params is not None else n_slices
    
    return True
    

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
                
                #imp.show()
                
                IJ.log("Processing image pair {}: {}".format(n_files, root))
                
                continue_analysis = img_analysis(imp)
                if not continue_analysis:
                    IJ.log("Analysis stopped by user.")
                    break
                
                # Cleanup
                clear_results_and_rois()
                close_image(imp)
    
    close_all_images()
    IJ.log("Finished processing {} files.".format(n_files))


if __name__ == "__main__":
    main()
