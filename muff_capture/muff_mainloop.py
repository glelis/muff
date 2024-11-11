#! /usr/bin/python3
# Last edited on 2018-09-04 18:49:15 by stolfilocal

HELP = \
  "  muff_mainloop.py {nL} {nV} {nH} {Z_step}\n"

INFO = \
  "  This is the core process in the MUFF 2.0 microscope positioner software suite.  Its task is to loop through the various light settings, view directions, and camera positions. It interacts with the user (through {stderr} and {stdin}), with the Arduino firmware (through a serial port), and with the camera monitoring and grabbing process {muff_camview.py} (through named Linux pipes \"muff_pipe_m2c\" and \"muff_pipe_c2m\").\n" \
  "\n" \
  "  The command line arguments are the number {nL} of distinct lighting conditions, the number of {nV} viewing directions, the number {nH} of microscope Z positions (frames per stack), and the distance {Z_step} between consecutive positions (float, in millimeters).  Currently the number of views must be 1.\n" \
  "\n" \
  "  In normal operation, this process should be started with its {stdout} connected to the {stdin} of the process {muff_camview.py}.  It can be started alone for debugging, but then no frames will be grabbed or displayed.\n" \
  "\n" \
  "  The Arduino development environment is needed only to download the firmware to the Arduino.  Positioning of the microscope at the starting Z coordinate is done through this process, too.\n" \
  "\n" \
  "  The images are written with names '{muff_scans}/{datetime}/L{nn}/V{vv}/raw/frame_{fffff}.jpg', where {nn} is the index of the lighting setup (2 digits, from 00), {vv} is the view index (ditto), and {fffff} is the frame index (5 digits, from 0).  The {datetime} is the UTC date, hour, and minute when the program was started."

import os, sys, time, serial, re, muff_arduino, muff_params
from datetime import datetime
from sys import stdin, stdout, stderr

# Global parameters:
num_LEDs =  muff_arduino.num_LEDs   # Number of LEDs on the MUFF v2.0 lighting dome.

Z_step_min = -0.999   # Minimum step in Z coordinates (mm).
Z_step_max = +0.999   # Maximum step in Z coordinates (mm).
Z_range_max = 100.00  # Max Z position range (mm).
nL_max = num_LEDs    # Max number of lighting conditions.
nV_max = 1           # Max viewing directions.
nH_max = 99          # Max number of frames in each stack.

use_uvc = False # Grabbing module: {True = uvccapture}, {False = muff_camview.py}.

arduino_present = False   # Set to false if debugging without the Arduino.
camera_present = True     # Set to false if debigging without the frame grabbing software.
verbose = False      # True to print debugging info.

# Presumed state of the MUFF positioner:
Z_curr = None        # Current Z position, measured from lowest Z position in stack.
LED_status = [ None ] * num_LEDs  # Current state of all LEDs.
# ----------------------------------------------------------------------

def main():
  """Main program."""
  
  global arduino_present, verbose
  
  # If the user so requested print help and exit:
  muff_params.check_for_help(HELP,INFO)
  
  # For terminate_process:
  (sport,m2cPipe, c2mPipe) = (None, None, None)
  
  # Parse arguments from the command line:
  (ok,nL,nV,nH,Z_step) = parse_command_line_args()
  if not ok: terminate_process(sport,ok)
  
  # Create pipes to the frame grabber program:
  (m2cPipe,c2mPipe) = open_pipes()
  
  # Connect to the Arduino through a serial port:
  sport = muff_arduino.connect(arduino_present,verbose)
  
  # Test the leds and turn them all off:
  test_lighting_conditions(sport,nL)
  
  # Define the vertical displacement between frames in each stack:
  muff_arduino.set_Z_step(sport,Z_step)

  # Ask user to manually position the microscope at first height:
  ok = place_camera_for_first_image(sport)
  if not ok: terminate_process(sport,m2cPipe,c2mPipe,ok)

    
  # Capture the images:
  ok = capture_image_set(sport,m2cPipe,c2mPipe,nL,nV,nH, Z_step)

  # Finalization:
  terminate_process(sport,m2cPipe,c2mPipe,ok)
  
  assert False # Should not get here.
# ----------------------------------------------------------------------

def capture_image_set(sport, m2cPipe, c2mPipe, nL,nV,nH, Z_step):
  """Captures a complete MUFF image set, consisting of a 
  multi-focus image stack for each of {nL} lighting conditions and {nV}
  view directions.  Each stack will have {nH} images, at equally
  spaced microscope heights, starting at the current position and
  rising by {Z_step} millimeters at every turn.  
  
  Interacts with the Arduino through the serial port {sport}.
  
  If {use_uvc} is false, interacts with the camera monitoring and frame grabbing
  program {muff_camview.py} through the pipe objects {m2cPipe,c2mPipe}.  
  Namely, sends cature requests through {m2cPipe}, and waits for
  completion replies through {c2mPipe}.
  
  Returns {True} if finished successfully, {False} if aborted.
  Also increments the assumed current position {Z_curr} by {Zstep}."""
  
  global Z_curr
  
  # Parameter checks:
  assert type(nL) is int and nL > 0 and nL <= nL_max     
  assert type(nV) is int and nV > 0 and nV <= nV_max   
  assert type(nH) is int and nH > 0 and nH <= nH_max   
  assert type(Z_step) is float and Z_step >= Z_step_min and Z_step <= Z_step_max
  assert nH*Z_step <= Z_range_max + 0.0001 # Fudged for rounding.
  
  # Compute number of images and estimated time:
  nI = nL*nV*nH;
  stderr.write("[muff_mainloop:] capturing %d images (%d lights, %d views, %d heights)\n" % (nI,nL,nV,nH))
  eTime = estimate_secs(nL,nV,nH)
  stderr.write("[muff_mainloop:] estimated time = %.1f minutes\n" % (eTime/60))
  
  # Create the directory tree:
  topdir = create_directories(nL,nV);
  stderr.write("[muff_mainloop:] saving images in directory %s\n" % topdir)
  
  # Capture all images: 
  tstart = time.time()
  for H in range(nH):
  
    if H > 0:
      # Move the microscope to the next Z position:
      muff_arduino.move_microscope(sport)
      Z_curr = Z_curr + Z_step
    
    # Capture all frames for this Z position:
    for V in range(nV):
    
      if nV > 1:
        # Rotate the object to viewing direction {V}:
        set_view_direction(sport,V,nV) 
        
      # Capture all frames for this {Z} position and view direction:
      for L in range(nL):
        
        # Choose the set of LEDs to use, and turn them on:
        LED_vals = define_LED_vals(L, nL) 
        set_light_condition(sport,LED_vals)
        
        # Grab the frame and save it to disk:
        ok = capture_frame(m2cPipe,c2mPipe,topdir,L,V,H)
        
        # Turn the  off:
        switch_all_lights_off(sport)
        
        # Abnormal exit: 
        if not ok: 
          stderr.write("** [muff_mainloop:] frame capture failed\n")
          return False
    
  tstop = time.time();
  stderr.write("[muff_mainloop:] captured %d images in %.1f minutes\n" % (nI, (tstop - tstart)/60))
  return True
# ----------------------------------------------------------------------

def place_camera_for_first_image(sport):
  """Ask the user to position the microscope camera at the lowest Z value,
  using the buttons on the microscope stand, the commands '1'/'2'/'6'/'7'/'3' through the
  Arduino interface, or the keys 'u'/'d'/'U'/'D'/'s' on the PC keyboard.  
  Returns {True} if the attempt succeeded, and {False} if the user
  aborted by typing 'abort', 'q', or CTRL+D.  Accepts upper or lower case.
  
  The function sets the global assumed position {Z_curr} to 0."""
  
  global Z_curr
  
  help = """
      Manually position the microscope camera at the 
      lowest Z1 position of the stack.  

      Type
        'u[ENTER]' to start the microscope moving up (slow), 
        'U[ENTER]' to start the microscope moving up (fast), 
        'd[ENTER]' to start it moving down (slow), 
        'D[ENTER]' to start it moving down (fast), and 
        's[ENTER]' to stop the motion.  
      You may repeat these commands as many times as needed.

      When the camera is at the desired starting position, type 
        'ok[ENTER]'.

      To abort the capture, type 
        'abort[ENTER]', or  
        'q[ENTER]', or 
        '[CTRL D]'.
      """
  
  stderr.write("[muff_mainloop:] starting manual positioning of the camera.\n")
  stderr.write(re.sub("\n      ", "\n", help))
  
  # Turn on some leds:
  Lval = [ 0.0 ] * num_LEDs;
  for index in (0, 3, 6, 9): # Four LEDs on top tier.
    Lval[index] = 1.0
  set_light_condition(sport,Lval)
  
  # Adjust the camera according to user commands:
  while True:
    stderr.write("[muff_mainloop:] command (u,d,U,D,s,q,ok,abort)? ");
    stderr.flush()
    s = stdin.readline()
    if s == "":
      # End of file:
      stderr.write("\n")
      stderr.flush()
      muff_arduino.stop_motor(sport)
      return False
    # Not end-of file:
    s = s.strip() # Remove leading and trailing whitespace, including EOL.
    if s.lower() == "ok":
      muff_arduino.stop_motor(sport)
      # Define this as the {Z = 0} position:
      Z_curr = 0.0
      return True
    elif s.lower() == "abort" or s.lower() == "q":
      muff_arduino.stop_motor(sport)
      return False
    elif s == "u":
      muff_arduino.start_motor(sport,+1,False)
    elif s == "d":
      muff_arduino.start_motor(sport,-1,False)
    elif s == "U":
      muff_arduino.start_motor(sport,+1,True)
    elif s == "D":
      muff_arduino.start_motor(sport,-1,True)
    elif s.lower() == "s":
      muff_arduino.stop_motor(sport)
    elif s == "":
      # User typed blank line and [ENTER]:
      pass
    else:
      # Complain and insist:
      stderr.write("** unrecognized command '%s'\n" % show_chars(s,True))
      stderr.flush()
      
  # Turn leds off:
  switch_all_lights_off(sport) 
  
# ----------------------------------------------------------------------

def capture_frame(m2cPipe,c2mPipe,topdir,L,V,H):
  """Issues a call to the external image capture software to grab one
  frame from the microscope, assumed to be for lighting schema {L}, view
  direction {V}, and microscope height {H}. Assumes that the lights,
  view, and microscope have been physically set as appropriate. Writes
  the image file in the proper subdirectory of {topdir}.
  
  If the global variable {use_uvc} is true, uses the UVC software {uvccapture},
  else sends a command to {muff_camview.py} through the pipe objects
  {m2cPipe,c2mPipe}.
  
  Returns {True} if success. Returns {False} (or aborts with error) on failure."""
  
  global use_uvc;
  
  # Compose the file name:
  fname = make_frame_filename(topdir, L, V, H)
  stderr.write("[muff_mainloop:] capturing frame %d and writing to '%s'\n" % (H,fname))
  
  # Call the external image capture program:
  if use_uvc:
    ok = capture_frame_uvc(fname)
  else: 
    ok = capture_frame_camview(m2cPipe,c2mPipe,fname)
  return ok
# ----------------------------------------------------------------------

def capture_frame_uvc(fname):
  """Start the {uvccapture} camera control program to grab one
  frame from the microscope and save it in file {fname}.
  Waits for 
  Returns {True} if success. Returns {False}
  (or aborts with error) on failure."""
  
  global camera_present
  
  template = "uvccapture -S40 -C30 -G80 -B20 -x2560 -y2048 -o'%s' -v"
  if verbose: stderr.write("[muff_mainloop:] grabbing frame with command = \"%s\"\n" % template)

  if not camera_present: 
    return True 
  else: # Capture with {uvccapture}:
    command = (template % fname)
    res = os.system(command)
  if res != 0:
    stderr.write("** [muff_mainloop:] {uvccapture} returned with nonzero status %d\n" % res)
    return False
  else:
    return True
# ----------------------------------------------------------------------
    
def capture_frame_camview(m2cPipe,c2mPipe,fname):
  """Issues through {m2cPipe} a command to the camera monitoring and 
  frame grabbing process {muff_camview.py} to grab one frame from the 
  microscope and save it in file {fname}.  Returns {True} if success. 
  Returns {False} (or aborts with error) on failure."""

  global camera_present
  
  # Send command to that process:
  command = "G " + fname
  if not camera_present:
    # Just pretend it was sent:
    if verbose: stderr.write("[muff_mainloop:] sending command to {muff_camview.py} '%s%\n" % command)
    return True
  else:
    try:
      m2cPipe.write(command)
      m2cPipe.write("\n")
      m2cPipe.flush()
    except:
      stderr.write("** [muff_mainloop:] command to {muff_camview.py} could not be sent\n")
      return False

    # Wait for it to complete the grabbing:
    s = c2mPipe.readline();
    if s == "":
      stderr.write("** [muff_mainloop:] pipe from {muff_camview.py} was closed\n")
      return False
    if s != "ok\n":
      stderr.write("** [muff_mainloop:] {muff_camview.py} returned invalid response '%s'\n" % show_chars(s,False))
      return False

    return True
# ----------------------------------------------------------------------
  
def estimate_secs(nL,nV,nH):
  """Returns the estimated time (seconds) for a scanning job
  with {nL} lighting conditions, {nV} view directions, and
  {nH} camera positions."""
  
  # Parameters to estimate the running time:
  mov_time = 2.00      # Estimated time to raise the microscope.
  rot_time = 3.00      # Estimated time to rotate object.
  img_time = 3.00      # Estimated time to set lighting and capture 1 image.

  # Compute time for 1 camera height and 1 view direction:
  eTime = img_time * nL

  # Account for object repositioning time.
  # Assume that a stage motion is needed at every direction, if more than 1.
  if nV > 1:
    eTime = (eTime + rot_time)*nV
  
  # Account for microscope camera motion time.
  # Assume that the first frame is grabbed at the current height.
  eTime = eTime * nH + mov_time * (nH-1)

  return eTime
# ----------------------------------------------------------------------  
  
def open_pipes():
  """If there is a camera and it is controlled by the {muff_camview}
  process, opens the pipes {m2cPipe,c2mPipe} for communication to and from 
  that process, and returns the pair of pipe objects.  Otherwise returns {(None,None)}."""
  
  global camera_present, use_uvc
  
  if camera_present and not use_uvc:   
    # Note: order is important to prevent blocking.
    m2cPipe = open("./muff_pipe_m2c", 'w')
    c2mPipe = open("./muff_pipe_c2m", 'r')
    return (m2cPipe, c2mPipe)
  else:
    stderr.write("[muff_mainloop:] !! assuming that {muff_camview.py} is not running\n")
    return (None, None)
# ----------------------------------------------------------------------
  
def create_directories(nL,nV):
  """Creates the directory structure for a scanset with {nL} distinct
  lighting conditions and {nV} distinct viewing directions.  Returns 
  the top level directory name, 'muff_scans/{date}-{minute}'.  Fails 
  if that directory exists.  If that happens, wait a minute and retry."""
  
  # Parameter checks (the "<= 99" is because of dir names):
  assert type(nL) is int and nL > 0 and nL <= 99 and nL <= nL_max     
  assert type(nV) is int and nV > 0 and nV <= 99 and nV <= nV_max   
  
  # Create the top level directory.  Fails if already exists.
  td = datetime.utcnow()             # UTC date and tofday. 
  tdx = td.strftime("%Y-%m-%d-%H%M-U") # Formatted UTC date, hour, minute.
  topdir = ("muff_scans/%s" % tdx)      # Top level directory name.
  if verbose: stderr.write("[muff_mainloop:] creating top directory '%s' and subdirectories\n" % topdir)
  os.makedirs(topdir,exist_ok=False)    # Create top level dir (must not exist).
  
  # Create subdirs for all lighting conditions and views:
  for L in range(nL):
    for V in range(nV):
      subdir = make_subdir_name(topdir, L, V) # Subdirectory name.
      if verbose: stderr.write("[muff_mainloop:] creating subdirectory '%s'\n" % subdir)
      os.makedirs(subdir,exist_ok=False)   # Create subdir (must not exist).
  
  return topdir
# ----------------------------------------------------------------------
  
def make_subdir_name(topdir, L, V):
  """Creates the subdirectory for all raw images with lighting condition {L} and view 
  direction {V}, in the top level directory {topdir}."""
  
  subdir = ("%s/L_%02d/V_%02d/raw" % (topdir, L, V))
  return subdir
# ----------------------------------------------------------------------

def make_frame_filename(topdir, L, V, H):
  """Creates the filename for the raw image with lighting condition {L}, view 
  direction {V}, and microscope height {H}, in the top level directory
  {topdir}."""
  
  subdir = make_subdir_name(topdir, L, V)
  fname = ("%s/frame_%05d.jpg" % (subdir,H))
  return fname
# ----------------------------------------------------------------------

def test_lighting_conditions(sport,nL):
  """Displays all lighting conditions {0..nL-1}.  Then 
  turns all LEDs off."""

  global LED_status
  
  # Flash all the leds on and off: */
  stderr.write("[muff_mainloop:] testing all %d leds\n" % num_LEDs)
  muff_arduino.test_lights(sport)
  LED_status = [ 0.0 ] * num_LEDs

  # Now flash the combinations that we will use:
  stderr.write("[muff_mainloop:] testing all %d lighting conditions to be used\n" % nL)
  for L in range(nL):
    stderr.write("[muff_mainloop:] setting lighting condition L%02d\n" % L) 
    LED_vals = define_LED_vals(L,nL)
    set_light_condition(sport,LED_vals)
    time.sleep(2.0)
    switch_all_lights_off(sport)
  return
# ---------------------------------------------------------------------- 
  
def define_LED_vals(L,nL):
  """Returns a list of {num_LEDs} LED intensity values (currently either 0.0 or 1.0)
  to use for lighting condition {L}, out of {nL} possible conditions.
  
  Currently, the number of lighting conditions {nL} must be 
  {num_LEDs} or less.  Lighting condition {L} has LED number {L}
  turned on and all other LEDs turned off.  If {nL} is less than {num_LEDs},
  only the first {nL} LEDs will be used.  This must be fixed once
  we know the position of each LED on the MUFF v2.0 dome.""" 
  
  assert type(nL) is int and nL > 0 and nL <= num_LEDs
  assert type(L) is int and L >= 0 and L < nL
  
  vals = [0.0] * num_LEDs
  
  # The following code assumes 24 LEDs in 2 tiers,
  # with same azimuths in both tiers, 30 deg apart,
  # sorted by azimuth clockwise in each tier.
  assert num_LEDs == 24
  if nL > 12:
    if L < 12 or nL == 24:
      # Single LEDs, 30 degrees apart, top tier:
      vals[L] = 1.0
    else:
      # Bottom tier, as equally spaced as possible:
      Lx = ((L - 12)*12 + 6)//(nL - 12)
      val[Lx] = 1.0
  elif nL == 12:
    # LED pairs on both tiers, same azimuth, 30 degrees apart:
    vals[L] = 1.0
    vals[L+12] = 1.0
  elif nL == 6:
    # Five LEDs, three on each tier, one oppposite on top tier for shadow filling:
    Lm = 2*L;            # Center LED on top tier.
    define_LED_centric_pattern(vals, Lm)
  else:
    assert nL < 12
    # Get azimuth as multiple of 15 degrees:
    S = (L*24 + 12)//nL
    assert S >= 0 and S < 23
    if S % 2 == 0:
      # Same pattern as 6 leds:
      Lm = S//2 
      define_LED_centric_pattern(vals, Lm)
    else:
      # Another pattern:
      La = (S - 1)//2
      define_LED_bridging_pattern(vals, La)
    
  return vals
# ----------------------------------------------------------------------

def define_LED_centric_pattern(vals, Lm):
  """Sets {vals[k]} to 1.0 for a pattern six LEDs centered
  on LED number {Lm}, which must be in {0..11}.
  The pattern has four main LEDs clustered near {Lm}
  and two more at about 120 deg from them, to provide shadow fill."""
  
  assert Lm >= 0 and Lm < 12
  # Four main LEDs:
  vals[Lm] = 1.0   
  La = (Lm +  1) % 12; vals[La] = 1.0  # Next LED on top tier.
  Lb = (Lm + 11) % 12; vals[Lb] = 1.0  # Prev LED on top tier.
  Lu = Lm + 12;        vals[Lu] = 1.0  # Center LED on bottom tier.
  # Two shadow fillers:
  Lr = (Lm +  4) % 12; vals[Lr] = 1.0  
  Ls = (Lm +  8) % 12; vals[Ls] = 1.0
  return
# ----------------------------------------------------------------------  
  
def define_LED_bridging_pattern(vals, La):
  """Sets {vals[k]} to 1.0 for a pattern six LEDs centered
  between LED {La} (which must be in {0..11}) and the next
  LED {Lb=(La+1)%12}.   The pattern has four main LEDs 
  near {La,Lb} and two more at about 120 deg from them,
  to provide shadow fill."""
  
  assert La >= 0 and La < 12
  # Four main LEDs:
  vals[La] = 1.0   
  Lb = (La +  1) % 12; vals[Lb] = 1.0  # Next LED on top tier.
  Lu = La + 12; vals[Lu] = 1.0  # LED just below {La}.
  Lv = Lb + 12; vals[Lv] = 1.0  # LED just below {Lb}.
  # Two shadow fillers:
  Lr = (Lb +  4) % 12; vals[Lr] = 1.0  
  Ls = (La +  8) % 12; vals[Ls] = 1.0
  return
# ----------------------------------------------------------------------  
  
def set_light_condition(sport,LED_vals):
  """Sends to the arduino commands to turn the lights specified in {LED_vals} on. 
  The parameter {LED_vals} must be a list of {num_LEDs} intensities
  (currently either 0.0 or 1.0).  Assumes that the current status
  of all leds is the global variable {LED_status}, which is 
  updated accordingly."""
  
  global LED_status
  assert len(LED_vals) == num_LEDs

  for lix in range(num_LEDs):
    pwr = LED_vals[lix] # Desired intensity of LED {lix}:
    assert type(pwr) is float and pwr == 0.0 or pwr == 1.0
    if pwr != LED_status[lix]:
      # Must change state of LED {lix}:
      muff_arduino.switch_LED(sport, lix, pwr)
      LED_status[lix] = pwr
# ----------------------------------------------------------------------
  
def switch_all_lights_off(sport):
  """Sends commands to the Arduino to turn off all the LEDs.
  Records that state in {LED_status}."""
  
  global LED_status
  
  muff_arduino.switch_all_LEDs(sport,0.0);
  for lix in range(num_LEDs):
    LED_status[lix] = 0.0
  return
# ----------------------------------------------------------------------

def set_view_direction(sport,V,nV):
  """Sends commands to the Arduino to rotate the object to the 
  view direction number {V} out of {nV} possible views. 
  Will make sense only when there is a mechanized stage.""" 
  
  assert type(nV) is int and nV == 1
  assert type(V) is int and V >= 0 and V < nV
  if nV > 1:
    if verbose: stderr.write("[muff_mainloop:] rotating object to view direction %d\n" % V)
  return
# ----------------------------------------------------------------------

def show_chars(s, blanks):
  """Given a string {s}, returns a version of {s}
  with each non-printing char in {s} replaced by '[chr({NNN})]',
  where {NNN} is the character's decimal {ord}.  Also replaces 
  quotes, brackets, parentheses. If {blanks} is true, 
  replaces blanks too."""
  
  n = len(s)
  res = ""
  bad = "\'\"[]()" # Printable characters that should be converted too.
  for i in range(n):
    c = s[i]
    if (c == ' ' and blanks) or (c < ' ') or (c > '~') or (c in bad):
      # Show chr code:
      res = res + ("[chr(%03d)]" % ord(c))
    else:
      res = res + chr(ord(c))
  return res
# ----------------------------------------------------------------------

def parse_command_line_args():
  """Parses the command line arguments and 
  returns the scan set parametes.  If succeeds,
  returns {(True,nL,nV,nH,Z_step)}.  If something goes wrong,
  returns {(False,None,None,None,None)}."""
  
  if len(sys.argv) != 5 or sys.argv[1] == "-help":
    # Display the help text and exit:
    stderr.write("SYNOPSIS\n")
    stderr.write(HELP + "\n\n")
    stderr.write("DESCRIPTION\n")
    stderr.write(INFO + "\n")
    
  
  # Get data from command line:
  # Should check syntax and give error messages:
  try:
    nL = int(sys.argv[1])
    nV = int(sys.argv[2]) 
    nH = int(sys.argv[3])
    Z_step = float(sys.argv[4])
  except:
    stderr.write("** [muff_mainloop:] bad command line arguments '%s'\n" % ("' '".join(sys.argv)))
    stderr.write(HELP + "\n\n")
    return (False,None,None,None,None)
  
  return (True,nL,nV,nH,Z_step)
# ----------------------------------------------------------------------  
  
def terminate_process(sport,m2cPipe,c2mPipe,ok):
  """Terminates the process with exit status 0 if {ok} is true,
  status 1 if {ok} is false. Also commands to the Arduino to 
  turn off all LEDs and stop the motor. """
  
  # Close the pipes, if any:
  if m2cPipe != None: m2cPipe.close()
  if c2mPipe != None: c2mPipe.close()
  
  # Ensure that the positioner is in a nice state:
  muff_arduino.stop_motor(sport)
  muff_arduino.switch_all_LEDs(sport,0.0)
    
  if ok:
    stderr.write("[muff_mainloop:] done.\n")
    sys.exit(0)
  else:
    stderr.write("** [muff_mainloop:] process aborted.\n")
    sys.exit(1)
  assert False # Never gets here.
# ----------------------------------------------------------------------

main()



        
