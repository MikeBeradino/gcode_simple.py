from tkinter import filedialog
from tkinter import *
import tkinter.scrolledtext as st
import xml.etree.ElementTree as ET
import os
import sys
import re
###########################################################
#used to generate Gcode
###########################################################
# Local Imports
sys.path.insert(0, './lib') # (Import from lib folder)
import shapes as shapes_pkg
from shapes import point_generator
DEBUGGING = True
SVG = set(['rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'path'])
#############################################################
root = Tk()
root.geometry("800x300")  # Width x Height
root.title("EZ_Gcode")

def openSVG():
    # *** open file ***
    root.SVGfile = filedialog.askopenfilename(initialdir="SVGS/", title="Select file", filetypes=(
    ("SVG files", "*.svg"), ("all files", "*.*")))
    print ("opening file at  " +str(root.SVGfile))

def openfile():
    # *** open file ***
    root.filename = filedialog.askopenfilename(initialdir="images/", title="Select file", filetypes=(
    ("jpeg files", "*.jpg"),("png files", "*.png"), ("all files", "*.*")))
    print ("opening file at  " +str(root.filename))

def close_window():
    root.destroy()

def openSVG():
    # *** open file ***
    root.SVGfile = filedialog.askopenfilename(initialdir="SVGS/", title="Select file", filetypes=(
    ("SVG files", "*.svg"), ("all files", "*.*")))

    print ("opening file at  " +str(root.SVGfile))

def savefile():
    # *** save_file ***
    root.filenamesave = filedialog.asksaveasfilename(initialdir="images/", title="Select file", filetypes=(("jpeg files", "*.jpg"), ("all files", "*.*")))
    print("saving file to "+ root.filenamesave)

##################################################
### gcode generater

# name-files-according to origional name
# auto drop multi file
# auot offset
##################################################
def generate_gcode(filename):
    start,pre,post,end,pen_up,pen_down,pen_motor,XY_feed_rate,Pen_feed_rate,Homing,SVG_Width,SVG_Height = gcode_menu()

    '''G-code emitted at the start of processing the SVG file'''
    preamble = start

    '''G-code emitted at the end of processing the SVG file'''
    postamble = end

    '''G-code emitted before processing a SVG shape G4 is the command for dwell P is the time in ms'''
    shape_preamble = "G0 "+ pen_motor + pen_down+ " "+ Pen_feed_rate+"\n"

    '''G-code emitted after processing a SVG shape'''
    shape_postamble =  "G0 " + pen_motor + pen_up+ " "+ Pen_feed_rate+"\n"


    # A4 area:               210mm x 297mm
    # Printer Cutting Area: ~178mm x ~344mm
    # Testing Area:          150mm x 150mm  (for now)
    canvas_width = int(SVG_Width.get())
    canvas_height = int(SVG_Height.get())
    #hard coding to test this
    #canvas_width = int(600)
    #canvas_height = int(400)

    '''Print bed width in mm'''
    bed_max_x = canvas_width

    '''Print bed height in mm'''
    bed_max_y = canvas_height

    ''' Used to control the smoothness/sharpness of the curves.
        Smaller the value greater the sharpness. Make sure the
        value is greater than 0.1'''
    smoothness = 0.2


    ''' The main method that converts svg files into gcode files.
        Still incomplete. See tests/start.svg'''
    # *** open file ***


    # Check File Validity

    if not os.path.isfile(filename):
        raise ValueError("File \"" + filename + "\" not found.")

    if not filename.endswith('.svg'):
        raise ValueError("File \"" + filename + "\" is not an SVG file.")

    # Define the Output
    # ASSUMING LINUX / OSX FOLDER NAMING STYLE
    log = ""
    log += debug_log("Input File: " + filename)

    file = filename.split('/')[-1]
    dirlist = filename.split('/')[:-1]
    dir_string = ""
    for folder in dirlist:
        dir_string += folder + '/'

    # Make Output File
    outdir = dir_string + "gcode_output/"
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    outfile = outdir + file.split(".svg")[0] + '.gcode'
    log += debug_log("Output File: " + outfile)

    # Make Debug File
    debugdir = dir_string + "log/"
    if not os.path.exists(debugdir):
        os.makedirs(debugdir)
    debug_file = debugdir + file.split(".svg")[0] + '.log'
    log += debug_log("Log File: " + debug_file + "\n")

    # Get the SVG Input File
    file = open(filename, 'r')
    tree = ET.parse(file)
    root = tree.getroot()
    file.close()

    # Get the Height and Width from the parent svg tag
    width = root.get('width')
    height = root.get('height')
    if width == None or height == None:
        viewbox = root.get('viewBox')
        if viewbox:
            _, _, width, height = viewbox.split()

    if width == None or height == None:
        # raise ValueError("Unable to get width or height for the svg")
        print("Unable to get width and height for the svg")
        sys.exit(1)

    # Scale the file appropriately
    # (Will never distort image - always scales evenly)
    # ASSUMES: Y ASIX IS LONG AXIS
    #          X AXIS IS SHORT AXIS
    # i.e. laser cutter is in "portrait"
    width = re.sub('[^0-9^.]', '', width)
    height = re.sub('[^0-9^.]', '', height)

    scale_x = bed_max_x / float(width)
    scale_y = bed_max_y / float(height)
    scale = min(scale_x, scale_y)
    if scale > 1:
        scale = 1

    log += debug_log("wdth: " + str(width))
    log += debug_log("hght: " + str(height))
    log += debug_log("scale: " + str(scale))
    log += debug_log("x%: " + str(scale_x))
    log += debug_log("y%: " + str(scale_y))

    # CREATE OUTPUT VARIABLE
    gcode = ""

    # Write Initial G-Codes
    gcode += preamble + "\n"

    # Iterate through svg elements
    for elem in root.iter():
        log += debug_log("--Found Elem: " + str(elem))
        new_shape = True
        try:
            tag_suffix = elem.tag.split("}")[-1]
        except:
            print("Error reading tag value:", tag_suffix)
            continue

        # Checks element is valid SVG shape
        if tag_suffix in SVG:

            log += debug_log("  --Name: " + str(tag_suffix))

            # Get corresponding class object from 'shapes.py'
            shape_class = getattr(shapes_pkg, tag_suffix)
            shape_obj = shape_class(elem)

            log += debug_log("\tClass : " + str(shape_class))
            log += debug_log("\tObject: " + str(shape_obj))
            log += debug_log("\tAttrs : " + str(list(elem.items())))
            log += debug_log("\tTransform: " + str(elem.get('transform')))

            ############ HERE'S THE MEAT!!! #############
            # Gets the Object path info in one of 2 ways:
            # 1. Reads the <tag>'s 'd' attribute.
            # 2. Reads the SVG and generates the path itself.
            d = shape_obj.d_path()
            log += debug_log("\td: " + str(d))

            # The *Transformation Matrix* #
            # Specifies something about how curves are approximated
            # Non-essential - a default is used if the method below
            #   returns None.
            m = shape_obj.transformation_matrix()
            log += debug_log("\tm: " + str(m))

            if d:
                log += debug_log("\td is GOOD!")


                points = point_generator(d, m, smoothness)
                #gcode += shape_preamble + "\n"

                log += debug_log("\tPoints: " + str(points))

                for x, y in points:
                    # log += debug_log("\t  pt: "+str((x,y)))

                    x = scale * x
                    y = bed_max_y - scale * y

                    log += debug_log("\t  pt: " + str((x, y)))

                    if x >= -10000000 and x <= bed_max_x + 10000000000 and y >= -1000000000 and y <= bed_max_y + 100000000000:
                        if new_shape:
                            gcode += ("G0 X%0.1f Y%0.1f\n" % (x, y))
                            #make sure to move with the pen up
                            gcode += shape_preamble + "\n"
                            gcode += ("G0 X%0.1f Y%0.1f\n" % (x, y))
                            #gcode += "M03\n" spindel on
                            new_shape = False
                        else:
                            gcode += ("G0 X%0.1f Y%0.1f\n" % (x, y))
                        log += debug_log("\t    --Point printed")
                    else:
                        log += debug_log("\t    --POINT NOT PRINTED (" + str(bed_max_x) + "," + str(bed_max_y) + ")")
                gcode += shape_postamble + "\n"
            else:
                log += debug_log("\tNO PATH INSTRUCTIONS FOUND!!")
        else:
            log += debug_log("  --No Name: " + tag_suffix)

    gcode += postamble + "\n"

    sample_gcode(gcode)
    # Write the Result
    ofile = open(outfile, 'w+')
    ofile.write(gcode)
    ofile.close()

    # Write Debugging
    if DEBUGGING:
        dfile = open(debug_file, 'w+')
        dfile.write(log)
        dfile.close()
#opens svg file selector

def svg_for_gcode():
    root.SVGfile = filedialog.askopenfilename(initialdir="Layers/", title="Select file", filetypes=(
    ("SVG files", "*.svg"), ("all files", "*.*")))
    file = str(root.SVGfile)
    generate_gcode(file)
#log for gcode generator

def debug_log(message):
    ''' Simple debugging function. If you don't understand
        something then chuck this frickin everywhere. '''
    #if (DEBUGGING):
    #    print(message)
    return message + '\n'
#used in generate gcode

def sample_gcode(gcode_preview):
    Label(root, text="Gcode", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=520, y=10,height=20,width=100)
    Gcode_Text = st.ScrolledText(root,font=("Times New Roman", 15))
    Gcode_Text.insert(INSERT, gcode_preview)
    Gcode_Text.place(x=520, y=30, height=230, width=200)

def gcode_menu():
    with open("gcode_default.ini", "r") as gcode_defaults:
            commands = gcode_defaults.read()

    str_XY_FEED_Rate_mm_dirty = re.search(r'XY_FEED_Rate_mm.*?Pen_Down_FEED_Rate_mm', commands, re.DOTALL).group()
    str_XY_FEED_Rate_mm = str_XY_FEED_Rate_mm_dirty.replace("XY_FEED_Rate_mm\n", "").replace("Pen_Down_FEED_Rate_mm", "").replace("\n","")

    str_Pen_Down_FEED_Rate_mm_dirty = re.search(r'Pen_Down_FEED_Rate_mm.*?PEN_UP_HIGHT_mm', commands, re.DOTALL).group()
    str_Pen_Down_FEED_Rate_mm = str_Pen_Down_FEED_Rate_mm_dirty.replace("Pen_Down_FEED_Rate_mm\n", "").replace("PEN_UP_HIGHT_mm", "").replace("\n","")

    str_PEN_UP_HIGHT_mm_dirty = re.search(r'PEN_UP_HIGHT_mm.*?PEN_DOWN_HIGHT_mm', commands, re.DOTALL).group()
    str_PEN_UP_HIGHT_mm = str_PEN_UP_HIGHT_mm_dirty.replace("PEN_UP_HIGHT_mm\n", "").replace("PEN_DOWN_HIGHT_mm", "").replace("\n","")

    str_PEN_DOWN_HIGHT_mm_dirty = re.search(r'PEN_DOWN_HIGHT_mm.*?Pen_Motor', commands, re.DOTALL).group()
    str_PEN_DOWN_HIGHT_mm = str_PEN_DOWN_HIGHT_mm_dirty.replace("PEN_DOWN_HIGHT_mm\n", "").replace("Pen_Motor", "").replace("\n","")

    str_Pen_dirty = re.search(r'Pen_Motor.*?Homing', commands, re.DOTALL).group()
    str_Pen = str_Pen_dirty.replace("Pen_Motor\n", "").replace("Homing", "").replace("\n","")

    str_Homing_dirty = re.search(r'Homing.*?Start', commands, re.DOTALL).group()
    str_Homing = str_Homing_dirty.replace("Homing\n", "").replace("Start", "").replace("\n","")

    str_start_dirty = re.search(r'Start.*?Pre_move', commands, re.DOTALL).group()
    str_start = str_start_dirty.replace("Start\n", "").replace("Pre_move", "")

    str_pre_dirty = re.search(r'Pre_move.*?Post_move', commands, re.DOTALL).group()
    str_pre = str_pre_dirty.replace("Pre_move\n", "").replace("Post_move", "")

    str_post_dirty = re.search(r'Post_move.*?End', commands, re.DOTALL).group()
    str_post =  str_post_dirty .replace("Post_move\n", "").replace("End", "")

    str_end_diry = re.search(r'End.*?Finish', commands, re.DOTALL).group()
    str_end = str_end_diry.replace("End\n", "").replace("Finish", "")


    Label(root, text="Pen Motor", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=10, y=10,height=20, width=100)
    default_Pen_Text = StringVar(root, value= str_Pen)
    default_Pen_Text = Entry(root, textvariable=default_Pen_Text)
    default_Pen_Text.place(x=10, y=30, height=20, width=80)

    Label(root, text="XY_F_rate", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=10, y=50,height=20, width=100)
    default_XY_feed_Text = StringVar(root, value= str_XY_FEED_Rate_mm)
    default_XY_feed_Text = Entry(root, textvariable= default_XY_feed_Text)
    default_XY_feed_Text.place(x=10, y=70, height=20, width=80)

    Label(root, text="PEN_F_rate", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=10, y=90,height=20, width=100)
    PEN_FEED_RATE_Text = StringVar(root, value= str_Pen_Down_FEED_Rate_mm)
    PEN_FEED_RATE_Text = Entry(root, textvariable=PEN_FEED_RATE_Text)
    PEN_FEED_RATE_Text.place(x=10, y=110, height=20, width=80)

    Label(root, text="PEN_Up_pos", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=85, y=10,height=20, width=100)
    PEN_UP_HIGHT_mm_Text = StringVar(root, value= str_PEN_UP_HIGHT_mm)
    PEN_UP_HIGHT_mm_Text = Entry(root, textvariable=PEN_UP_HIGHT_mm_Text )
    PEN_UP_HIGHT_mm_Text.place(x=85, y=30, height=20, width=80)

    Label(root, text="PEN_Down_pos", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=85, y=50,height=20, width=100)
    PEN_DOWN_HIGHT_mm_Text = StringVar(root, value= str_PEN_DOWN_HIGHT_mm)
    PEN_DOWN_HIGHT_mm_Text = Entry(root, textvariable=PEN_DOWN_HIGHT_mm_Text )
    PEN_DOWN_HIGHT_mm_Text.place(x=85, y=70, height=20, width=80)

    Label(root, text="HOMING", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=85, y=90,height=20, width=100)
    str_Homing_Text = StringVar(root, value= str_Homing)
    str_Homing_Text = Entry(root, textvariable=str_Homing_Text)
    str_Homing_Text.place(x=85, y=110, height=20, width=80)

    Label(root, text="Start", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=190, y=10,height=20,width=100)
    Start_Text = st.ScrolledText(root, font=("Times New Roman", 15))
    Start_Text.insert(INSERT,str_start)
    Start_Text.place(x=190, y=30, height=100, width=150)
    # Placing cursor in the text area
    Start_Text.focus()

    Label(root, text="Pre_move", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=190, y=130,height=20,width=100)
    Pre_move_Text = st.ScrolledText(root,font=("Times New Roman", 15))
    Pre_move_Text.insert(INSERT,str_pre)
    Pre_move_Text.place(x=190, y=150, height=100, width=150)
    # Placing cursor in the text area
    Pre_move_Text.focus()

    Label(root, text="End", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=350, y=10,height=20, width=100)
    End_Text = st.ScrolledText(root,font=("Times New Roman", 15) )
    End_Text.insert(INSERT,str_end)
    End_Text.place(x=350, y=30, height=100, width=150)
    # Placing cursor in the text area
    End_Text.focus()

    Label(root, text="Post_move", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=350,y=130,height=20,width=100)
    Post_move_Text = st.ScrolledText(root,font=("Times New Roman", 15) )
    Post_move_Text.place(x=350, y=150, height=100, width=150)
    Post_move_Text.insert(INSERT,str_post)
    # Placing cursor in the text area
    Post_move_Text.focus()

    getfile = Button(root, text="SVG_for_Gcode", command=svg_for_gcode)

    getfile.place(x=10, y=205, height=40, width=150)

    return(str_start,str_pre,str_post,str_end,str_PEN_UP_HIGHT_mm,str_PEN_DOWN_HIGHT_mm,str_Pen,str_XY_FEED_Rate_mm,str_Pen_Down_FEED_Rate_mm,str_Homing,SVG_Width,SVG_Height)


Label(root, text="SVG_Width", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=10, y=130,height=20, width=100)
SVG_Width = StringVar(root, value= "")
SVG_Width = Entry(root, textvariable=SVG_Width)
SVG_Width.place(x=10, y=150, height=20, width=80)

Label(root, text="SVG_Height", anchor="w", bg="gray20", fg="lime green", font=("Times New Roman", 12)).place(x=85, y=130,height=20, width=100)
SVG_Height = StringVar(root, value= "")
SVG_Height = Entry(root, textvariable=SVG_Height)
SVG_Height.place(x=85, y=150, height=20, width=80)

root.configure(background='gray20')
gcode_menu()
root.SVGfile = ""
root.mainloop()