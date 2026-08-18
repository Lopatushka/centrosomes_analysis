from ij import IJ, WindowManager
from ij.plugin.frame import RoiManager
from ij.gui import WaitForUserDialog, GenericDialog
from ij.plugin import ChannelSplitter, ZProjector, RGBStackMerge
from ij.process import ImageStatistics, ImageConverter
from ij.gui import NonBlockingGenericDialog, WaitForUserDialog, PointRoi
from ij.measure import ResultsTable, Measurements
import os
import csv
import traceback

# ---------------------------------
# HELPERS
# ---------------------------------
def image_name(imp):
    return imp.getTitle().split(".")[0]

def safe_name(text):
    return text.replace(" ", "_").lower()

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
    

def max_projection(imp, first_slice, last_slice):
    """
    Create a maximum intensity projection between
    first_slice and last_slice.

    Parameters
    ----------
    imp : ImagePlus
        Input image stack.
    first_slice : int
        First slice to include.
    last_slice : int
        Last slice to include.

    Returns
    -------
    ImagePlus
        Maximum intensity projection.
    """

    zp = ZProjector(imp)

    zp.setStartSlice(first_slice)
    zp.setStopSlice(last_slice)
    zp.setMethod(ZProjector.MAX_METHOD)

    zp.doProjection()

    projection = zp.getProjection()

    return projection
    
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
           
def img_analysis(imp, output_dir):   
    imp_name = safe_name(image_name(imp))
    n_slices = imp.getNSlices()
    
    # Split channels
    channels = ChannelSplitter.split(imp)
    if len(channels) != 3:
        IJ.log("Image {} does not have 3 channels!".format(imp_name))
        return True
    
    c1 = channels[0] # DAPI channel
    c2 = channels[1] # MEARGUREMENT 1
    c3 = channels[2] # MEARGUREMENT 2
       
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
    
    IJ.log("Keep slices {} - {}".format(first_slice, last_slice))
    
    # Make maximum intensity projection
    proj1 = max_projection(c1, first_slice, last_slice) # DAPI BLUE
    proj2 = max_projection(c2, first_slice, last_slice) # MEASUREMENT 1 GREEN
    proj3 = max_projection(c3, first_slice, last_slice) # MEASUREMENT 2 RED
    
    # Adjust brigthtness and contrast
    IJ.run(proj2, "Enhance Contrast", "saturated=0.05 normalize")
    IJ.run(proj3, "Enhance Contrast", "saturated=0.05 normalize")
       
    # Merge channels: RED GREEN BLUE
    merge1 = RGBStackMerge.mergeChannels([None, proj2, proj1, None, None, None, None], True)
    ImageConverter(merge1).convertToRGB()
    merge1.setTitle("merge1_{}".format(imp_name))
    
    merge2 = RGBStackMerge.mergeChannels([proj3, None, proj1, None, None, None, None], True)
    ImageConverter(merge2).convertToRGB()
    merge2.setTitle("merge2_{}".format(imp_name))
    
    # Show splitted images
    merge1.show()
    merge2.show()
    
    # Save merged images
    merge1_path = os.path.join(output_dir, image_name(merge1))
    IJ.save(merge1, merge1_path)
    
    merge2_path = os.path.join(output_dir, image_name(merge2))
    IJ.save(merge2, merge2_path)
    
    
    # Close images
    close_image(imp)
    
    close_image(c1)
    close_image(c2)
    close_image(c3)
    
    close_image(proj1)
    close_image(proj2)
    close_image(proj3)
    
    # ---------------------------------
    # Measurements
    # ---------------------------------   
    clear_results_and_rois()
    
    # Open ROI Manager if not already open
    rm = RoiManager.getInstance()
    if rm is None:
        rm = RoiManager()
        
    # Select multipoint tool
    IJ.setTool("multipoint")
    
    # Create an empty results table and show it
    rt = ResultsTable()
    
    # --- Iteration ---        
    n_cell = 0
    
    while True:
        # Clear ROI manager
        rm.reset()
        
        if n_cell > 0:
            IJ.log("Moving to the next cell in the image.")
        
        # Dialog with user
        gd = GenericDialog("Measurement")
        gd.addChoice(
                    "Measure single cell:",
                    ["Merge 1", "Merge2 ", "Next image"],
                    "Channel 1"
        )
        gd.showDialog()
        
        if gd.wasCanceled():
            measurement_type = "Next image"
        else:
            measurement_type = gd.getNextChoice()
            
        # Skip pair and go to next folder
        if measurement_type == "Next image":
            IJ.log("Moving to the next image.")
            break
                
        n_cell += 1
        
        count = 0
        
        while count < 1:
            # Clear ROI manager
            rm.reset()
             
            # Measure image 
            WaitForUserDialog(
                "Cell %s - %s" % (n_cell, measurement_type),
                "Select objects for Cell %s in %s.\n"
                "Click OK when finished." % (n_cell, measurement_type)
            ).show()
            
            # Re-fetch after user interaction in while loop
            rois = rm.getRoisAsArray()
            if len(rois) == 0:
                IJ.log("ROI Manager is empty. Moving to the next cell.")
                continue
            
            # Fill the table with results
            for i, roi in enumerate(rois):
                roi_name = roi.getName()
                if roi_name is None or roi_name.strip() == "":
                    roi_name = "ROI_%02d" % (i + 1) 
                
                rt.incrementCounter()
                rt.addValue("Image", imp_name)
                rt.addValue("Cell", n_cell)
                rt.addValue("Channel", measurement_type)
                rt.addValue("ROI", roi_name)
            
            # Show/update table
            rt.show("Results")
            
            count += 1
    
    IJ.log("Image is processed. Results are saved.")
    
    # Save results table as csv file
    results_name = "results_{}.csv".format(imp_name)
    results_path = os.path.join(output_dir, results_name)
    rt.save(results_path)
    
    # Close images after analysis   
    close_image(merge1)
    close_image(merge2)
    
    return True
    

# ---------------------------------
# MAIN FUNCTION
# ---------------------------------
def main():
    # Ask user about the folder with data
    input_dir = IJ.getDirectory("Choose a directory with data to analyze")
    if input_dir is None:
        return
    
    # Ask user where to save results
    output_dir = IJ.getDirectory("Choose a directory to save data")
    if output_dir is None:
        output_dir = input_dir
    IJ.log("Results will be saved in the directory: {}".format(output_dir))
    
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
                
                IJ.log("Processing image pair {}: {}".format(n_files, root))
                
                continue_analysis = img_analysis(imp, output_dir)
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
