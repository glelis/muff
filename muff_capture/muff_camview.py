#! /usr/bin/python3
# Last edited on 2018-07-13 23:39:08 by stolfilocal

HELP = \
  "  muff_camview.py {camix}\n"

INFO = \
  "  This is an auxiliary process in the MUFF 2.0 microscope positioner software suite.  Its task is to monitor the microscope camera, grab frames in response to external commands, and write them to disk.\n" \
  "\n" \
  "  The only command line argument is the index of the microscope camera in the system (0,1,2,etc.).  If there is no webcam, it is usually 0.  If there is a webcam, it will probably be 2.\n" \
  "\n" \
  "  This process opens a 'Current View' window, that continuously shows the current view of the camera in low resolution but (almost) real time; and a 'Grabbed Frame' window, that shows the last high-resolution frame that was grabbed and saved to disk.  The grabbed frame may be reduced for display, if too big.\n" \
  "\n" \
  "  This program reads commands from {stdin}, and writes an \"ok\\n\" confirmation to {stdout} after some commands.  In normal operation, these streams will be connected to named Linux pipes leading from/to the central program {muff_mainloop.py}.This process reads from {stdin} a sequence of camera comtrol commands.n" \
  "\n" \
  "  Either way, each command must be in a separate line.  Whitespace is generally ignored.\n" \
  "\n" \
  "Currently recognizes the following commands:\n" \
  "\n" \
  "  G{filename} - grab an image and write to {filename}. Responds with \"ok\\n\".\n" \
  "  #{anything} - comment, ignored.\n" \
  "  blank line - ignored.\n" \
  "  Q{anything} - quit."

import cv2, sys, os, re, select, time, muff_params
from sys import stdin, stderr, stdout

# Camera type (should be discovered automatically):
# cam_type = "Stolfi's Chinese microscope"
cam_type = "Celestron microscope without focus knob"
# cam_type = "Celestron microscope with focus knob"

# Desired frame sizes -- to be reset according to the camera type:
lo_img_size = (0, 0)   # Resolution to use when monitoring the current view.
hi_img_size = (0, 0)   # Resolution to use when grabbing frames.
hi_show_size = (0, 0)  # Resolution to use when showing grabbed frame.

# Current camera state:
curr_cam_size = (0, 0)     # Camera resolution as of last setting.

# Delay (seconds) to wait before grabbing a high-resolution image, to 
# allow for lighting/resolution changes to stabilize:
hires_grab_delay = 2.0

verbose = False    # If true, prints debugging info.

def main():
  """Main loop of the camera control process.
  Periodically grabs and displays an image from the camera,
  while waiting for commands to be entered through {stdin}."""
  
  # If the user so requested, print help and exit:
  muff_params.check_for_help(HELP,INFO)
    
  # Define the resolutions of monitoring and grabbed images based on camera type:
  choose_image_resolutions(cam_type)
  
  # Get command line arguments:
  (ok,camix) = parse_command_line_args()

  cam = cv2.VideoCapture(camix)  
  cam.set(cv2.CAP_PROP_FPS,10.0)
  
  # Create the 'real time' monitoring window:
  mwname = "Current View"
  cv2.namedWindow(mwname,cv2.WINDOW_AUTOSIZE)
  img = read_and_show_image(cam, mwname, False)
  
  # Create the 'last frame gabbed' window and show the 
  gwname = "Grabbed Frame"
  cv2.namedWindow(gwname,cv2.WINDOW_NORMAL)
  cv2.resizeWindow(gwname, hi_show_size[0], hi_show_size[1])
  img = read_and_show_image(cam, gwname, True)
  
  # Parameters for input monitoring:
  watchedStreams = [stdin] # Files to be monitored for input.
  timeout = 0.1 # Min seconds between monitor refresh.
  
  # Pattern of acceptable file names:
  filepat = re.compile(r'^[A-Za-z0-9_.][-A-Za-z0-9_./]*[.][a-zA-Z0-9]+$') 
  
  # Event loop:
  while True:
    readyStreams = select.select(watchedStreams, [], [], timeout)[0]
    if readyStreams == None or len(readyStreams) == 0:
      # Time out and no input command yet. Just refresh the monitor window.
      img = read_and_show_image(cam, mwname, False)
    else:
      # We got something on {stdin}.
      assert readyStreams[0] == stdin;
      cmd = stdin.readline()
      if len(cmd) == 0:
        # End of file
        stderr.write("[muff_camview:] input stream closed. Bye.\n")
        sys.exit(0)
      # We got at least the end-of-line:
      process_command(cam,cmd,gwname,filepat)

  cv2.destroyWindow(mwname)
  cv2.destroyWindow(gwname)
  return 0
# ----------------------------------------------------------------------

def process_command(cam,cmd,gwname,filepat):
  """Process one command {cmd}. 
  
  The command must end with and end-of-line character.
  Leading and trailing whitespace is ignored."""
  cmd = cmd.lstrip(' \t').rstrip(' \t\n\r')
  if verbose: stderr.write("[muff_camview:] got command [%s]\n" % show_chars(cmd,False))
  if len(cmd) == 0 or cmd[0] == '#':
    # Comment or blank line - ignore.
    pass
  elif cmd[0] == 'G':
    # Command to grab the image and save to disk.
    # Get the filename from the command:
    fname = cmd[1:].strip(" \t\n\r")
    if not filepat.match(fname):
      stderr.write("** [muff_camview:] invalid file name '%s'\n" % show_chars(fname,False))
      exit(1)
    # Grab the image and display it:
    img = read_and_show_image(cam, gwname, True)
    res = cv2.imwrite(fname,img)
    if res:
      if verbose: stderr.write("[muff_camview:] image saved (%dx%dx%d)\n" % img.shape)
    else:
      stderr.write("** [muff_camview:] image write failed\n")
    # Send the ok response:
    stdout.write("ok\n")
    stdout.flush()
  elif cmd[0] == 'Q' or cmd[0] == 'q':
    # Quit:
    stderr.write("[muff_camview:] quitting.\n")
    sys.exit(0)
  else:
    stderr.write("** [muff_camview:] unrecognized command '%s'\n" % cmd[0])
    sys.exit(1)
  return
# ----------------------------------------------------------------------

def choose_image_resolutions(ctype):
  """Sets the global variables {hi_img_size}, {lo_img_size},
  {hi_show_size} according to the camera type {ctype}.  
  
  The choices for {hi_img_size} and {lo_img_size} had better be
  supported by the camera, and should have the same aspect ratio and
  cover the same field of view. The choice {hi_show_size} is arbitary, but
  should have the same aspect ratio as the other two."""
  
  global hi_img_size, lo_img_size, hi_show_size
  if ctype == "Stolfi's Chinese microscope":
    # Available sizes: 
    #   4x3 aspect: 640x480, 320x240, 160x120
    #   11x9 aspect: 352x288, 176x144 
    lo_img_size = (320, 240)   # Resolution to use when monitoring the current view.
    hi_img_size = (640, 480)   # Resolution to use when grabbing frames.
    hi_show_size = (640, 480)  # Resolution to use when showing grabbed frame.
  elif ctype == "Celestron microscope without focus knob":
    # The one used for the MUFF v1.0. Available sizes: 
    #   4x3 aspect: 640x480, 320x240, 160x120, 1280x960 
    #   5x4 aspect: 1280x1024
    #   11x9 aspect: 352x288, 176x144 
    # The 1280x1024 size just crops to the middle region. 
    lo_img_size = (320, 240)   # Resolution to use when monitoring the current view.
    hi_img_size = (1280, 960)  # Resolution to use when grabbing frames.
    hi_show_size = (800, 600)  # Resolution to use when showing grabbed frame.
  elif ctype == "Celestron microscope with focus knob":
    # Available sizes: 
    #   4x3 aspect: 640x480, 320x240, 160x120, 800x600, 1280x960, 1600x1200
    #   11x9 aspect: 352x288, 176x144 
    # The 1280x960 size just crops to the middle region. 
    lo_img_size = (320, 240)   # Resolution to use when monitoring the current view.
    hi_img_size = (1600, 1200) # Resolution to use when grabbing frames.
    hi_show_size = (800, 600)  # Resolution to use when showing grabbed frame.
  else:
    assert False # Unknown camera type {ctype}.
  return
# ----------------------------------------------------------------------
  

def read_and_show_image(cam, wname, hires):
  """Grabs an image {img} with {read_image(cam,hires)} and 
  displays it on window {wname}.  Returns the image."""  
  
  # Grab the image:
  img = read_image(cam, hires)
  if verbose:
    show_camera_params(cam)
    sh = img.shape
    stderr.write("[muff_camview:] grabbed image:")
    stderr.write(" hires = %s shape = %dx%d channels = %d\n" % (str(hires),sh[1],sh[0],sh[2]))
  
  # Resize the image for display, if needed:
  if hires:
    img_show = cv2.resize(img, hi_show_size)
    sh = img_show.shape
    if verbose: stderr.write("[muff_camview:] resized image for display to %dx%d\n" % (sh[1],sh[0]))
  else:
    img_show = img
  cv2.imshow(wname,img_show)
  cv2.waitKey(1) # To get the image displayed.
  return img
# ----------------------------------------------------------------------

def read_image(cam, hires):
  """Grabs an image {img} from the camera. If the grab failed, prints an
  error and stops. Otherwise retursn {img}.
  
  The {hires} parameter specifies the desired resolution ({False} = low,
  {True} high).  If {hires} is true, waits for a while before grabbing.""" 
  
  global hires_grab_delay
  
  # Change camera resolution if needed:
  if hires:
    set_camera_resolution(cam, hi_img_size)
  else:
    set_camera_resolution(cam, lo_img_size)
    
  # Try to grab image:
  for trial in range(2):
    if trial > 0: stderr.write("!! [muff_camview:] image grab failed, retrying\n")
    if trial > 0 or hires:
      time.sleep(hires_grab_delay)
    s, img = cam.read()
    if s: break
  
  # Did we succeed:
  if not s: 
    stderr.write("** [muff_camview:] image grab failed, quitting")
    sys.exit(1)
  return img
# ----------------------------------------------------------------------

def set_camera_resolution(cam, size):
  """Changes the camera resolution to {size}, which must be
  a pair of integers {(width, heigh)} -- unless it is already set
  at that resolution.
  
  Uses and updates {curr_cam_size}."""
  
  global curr_cam_size
  if size != curr_cam_size:
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
    cv2.waitKey(1) # Do we need this?
    curr_cam_size = size
  return
# ----------------------------------------------------------------------


def show_camera_params(cam):
  """Prints to stderr the parameters of camera {cam}."""
  
  # OpenCV camera property names.  There seems to be no safe way
  # to find out via OpenCV what parameters and values are supported by a given
  # camera. Put "!" in front of a property name to disable querying it.
  props = [ 
    "--",
    "CAP_PROP_FRAME_WIDTH",           # Width of the frames in the video stream.
    "CAP_PROP_FRAME_HEIGHT",          # Height of the frames in the video stream.
    "CAP_PROP_FPS",                   # Frame rate (frames per second).
    "--",
    "CAP_PROP_BRIGHTNESS",            # Brightness of the image (only for cameras).
    "CAP_PROP_CONTRAST",              # Contrast of the image (only for cameras).
    "CAP_PROP_SATURATION",            # Saturation of the image (only for cameras).
    "CAP_PROP_HUE",                   # Hue setting of the image (only for cameras).
    "CAP_PROP_MODE",                  # Backend-specific value indicating current capture mode.
    "--",
    "CAP_PROP_POS_FRAMES",            # Index of current frame in video (starting from 0).
    "CAP_PROP_POS_MSEC",              # Current position in video (ms).
    "!CAP_PROP_POS_AVI_RATIO",         # Relative position in film (0 = start, 1 = end).
    "!CAP_PROP_FORMAT",                # Format of the {Mat} objects returned by {retrieve()}.
    "!CAP_PROP_CONVERT_RGB",           # Boolean flags indicating images should be converted to RGB.
    "!CAP_PROP_EXPOSURE",              # Exposure time (only for cameras).
    "!CAP_PROP_FOURCC",                # Four-character code of codec.
    "!CAP_PROP_FRAME_COUNT",           # Number of frames in video file.
    "!CAP_PROP_GAIN",                  # Gain of the image (only for cameras).
    "!CAP_PROP_RECTIFICATION",         # Rectification flag (for stereo cameras).
    "--",
    "!CAP_PROP_WHITE_BALANCE",         # Currently not supported by {cv2}.
    "!CAP_PROP_WHITE_BALANCE_BLUE_U",  # 
    "!CAP_PROP_MONOCHROME",            # 
    "!CAP_PROP_SHARPNESS",             # 
    "!CAP_PROP_AUTO_EXPOSURE",         # 
    "!CAP_PROP_GAMMA",                 # 
    "!CAP_PROP_TEMPERATURE",           # 
    "!CAP_PROP_TRIGGER",               #
    "!CAP_PROP_TRIGGER_DELAY",         # 
    "!CAP_PROP_WHITE_BALANCE_RED_V",   # 
    "!CAP_PROP_ZOOM",                  # 
    "!CAP_PROP_FOCUS",                 # 
    "!CAP_PROP_GUID",                  # 
    "!CAP_PROP_ISO_SPEED",             # 
    "!CAP_PROP_BACKLIGHT",             # 
    "!CAP_PROP_PAN",                   # 
    "!CAP_PROP_TILT",                  # 
    "!CAP_PROP_ROLL",                  # 
    "!CAP_PROP_IRIS",                  # 
    "!CAP_PROP_SETTINGS",              # 
    "!CAP_PROP_BUFFERSIZE",            # 
    "!CAP_PROP_AUTOFOCUS",             # 
    "!CAP_PROP_SAR_NUM",               #  Currently not supported by {cv2}?
    "!CAP_PROP_SAR_DEN",               #  Currently not supported by {cv2}?
  ]

  stderr.write("--- camera parameters ---\n")
  for pr in props:
    if pr == "--":
      # Spacer line:
      stderr.write("---------------------------------------\n")
    elif pr[0] == "!":
      # Do not query this property:
      pass
    else:
      # Get the property's numeric code and query the camera for it:
      prcode = int(eval("cv2." + pr)) # Numeric property code.
      val = cam.get(prcode)
      stderr.write(pr + " (%d) = %s\n" % (prcode,str(val)))
  return
# ----------------------------------------------------------------------

def show_chars(s, blanks):
  """Given a string {s}, returns a copy 
  with each non-printing char replaced by '[chr({NNN})]',
  where {NNN} is the character's decimal {ord}.  Also replaces 
  quotes, brackets, parentheses. If {blanks} is true, 
  replaces blanks too."""
  
  n = len(s)
  res = ""
  bad = "\'\"[]()" # Printable characters that should be converted too.
  for i in range(n):
    c = s[i]
    if (c == ' ' and blanks) or (c < ' ') or (c > '~') or (bad.find(c) >= 0):
      # Show chr code:
      res = res + ("[chr(%03d)]" % ord(c))
    else:
      res = res + c
  return res
# ----------------------------------------------------------------------
  
def parse_command_line_args():
  """ Parses the command line arguments.  Returns {(ok,...)} 
  where {ok} is true iff the parsing succeeded, and "..." are
  the parsed argment values (currently just {camix})."""
  
  # Initialize the camera:
  if len(sys.argv) == 2:
    try:
      camix = int(sys.argv[1]); # Camera index.
    except:
      stderr.write("** [muff_camview:] invalid camera index '%s'\n" % sys.argv[1])
      return (False, None)
  else:
    stderr.write("** [muff_camview:] invalid command line args '%s'\n" % ("' '".join(sys.argv)))
    return (False, None)
    
  return (True, camix)
# ----------------------------------------------------------------------

main()
