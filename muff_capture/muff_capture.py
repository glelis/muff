#! /usr/bin/python3
# Last edited on 2018-07-13 23:39:31 by stolfilocal

HELP = \
  "  muff_capture.py [ PARMFILE ]\n"

INFO = \
  "  This is the top-level program in the MUFF 2.0 microscope positioner software suite.  It automatically captures a complete multi-light, multi-view, multi-focus set of images of an object, suitable for 3D recovery using photometric, geometric, and focus stereo techniques.\n" \
  "\n" \
  "  The task of this program in fact is only to start the two processes that do the actual work, {muff_mainloop.py} and {muff_camview.py}, connected by appropriate Linux pipes.  The images are written to the directory '{muff_scans}'.  See those two programs for more details on the operation, such as the output file naming schema.\n" \
  "\n" \
  "  If the argument {PARMFILE} is specified, it must be the name of an existing text file.  The program reads from it, in order, the number {nL} of distinct light settings to use, the number {nV} of distinct viewing directions (which currently must be 1), the number {nH} of microscope Z positions (frames per stack), and the distance {Z_step} between consecutive positions (float, in millimeters).  If the {PARMFILE} is not specified, the program asks the user to input these parameters through {stdin}.  The program also asks the user for the index {camix} of the microscope camera in the system.\n" \
  "\n" \
  "  The number of distinct views is currently fixed at 1 due to the lack of an automatized tiltable stage.\n" \
  "\n" \
  "  The Arduino development environment is necessary only to download the firmware to the Arduino.  After that, the process {muff_mainloop.py} takes care of all interaction with the firmware."
  
import os, sys, muff_params
from sys import stderr

def main():
  """Main program."""
  
  # If the user so requested print help and exit:
  muff_params.check_for_help(HELP,INFO)
  
  # Get parameters:
  (ok,camix,params) = get_parameters()
  if not ok: terminate_process(False)
  
  # Start the two main programs:
  start_aux_programs(camix, params)
  
  terminate_process(True)
# ----------------------------------------------------------------------
  
def start_aux_programs(camix, params):
  """Starts the two auxiliary programs with the 
  necessary connections."""
  
  # Get the scanset parameters:
  nL = params["nL"];
  nV = params["nV"];
  nH = params["nH"];
  Z_step = params["Z_step"];
  
  # Create the pipes for interprocess communication:
  Pipes = ( "./muff_pipe_m2c", "./muff_pipe_c2m" )
  delete_pipes(Pipes) # Just in case.
  create_pipes(Pipes)

  # Start the camera monitoring process, don't wait for it to finish:
  camview_cmd = "./muff_camview.py %s < %s > %s &" % (camix, Pipes[0], Pipes[1])
  os.system(camview_cmd)
  
  # Start the main loop process, wait for it to finish:
  mainloop_cmd = "./muff_mainloop.py %d %d %d %+.3f" % (nL, nV, nH, Z_step)
  os.system(mainloop_cmd)

  # Cleanup:
  delete_pipes(Pipes)
# ----------------------------------------------------------------------  

def get_parameters():
  """Gets the scanset parameters from a parameter file and/or by asking
  the user to input them on stdin.
  
  Returns a tuple {(ok,camix,params)} where {ok} is true iff the
  function succeeded, {camix} is the camera index and {params} is a
  dictionary with fields "nL","nV","nH" (the numbers of lighting
  conditions, views, and heights), and "Z_step" (the vertical
  displacement between frames in mm). If any error occurs, returns a
  tuple with {ok = False}."""
  
  # Get the camera index always from the user:
  try:
    camix = muff_params.parse_int(input("camera index (usually 0 or 2)? "),"camix",False,0,99)
  except:
    stderr.write("** [muff_capture:] could not get the camera index\n")
    return (False, None, None)
  
  # Get the other parameters {params} from the user or from a file:
  if len(sys.argv) == 1:
    # Ask user to type parameters:
    params = muff_params.get_from_user()
  elif len(sys.argv) == 2:
    # Read parameters from a specified file:
    params_fname = sys.argv[1];
    stderr.write("[muff_capture:] reading parameters from file '%s'\n" % params_fname)
    params = muff_params.read_from_named_file(params_fname)
  else:
    stderr.write("** [muff_capture:] invalid command line args '%s'\n" % ("' '".join(sys.argv)))
    return (False,None,None)

  if params == None:
    stderr.write("** [muff_capture:] invalid parameters\n")
    return (False,None,None)

  return (True,camix,params)
# ----------------------------------------------------------------------  

def delete_pipes(L):
  """Removes the named Linux pipes listed in {L}, if they exist."""

  for pipe_name in L:
    try:
      os.remove(pipe_name)
    except:
      pass
# ----------------------------------------------------------------------  
  
def create_pipes(L):
  """Creates the named Linux pipes with the names listed in {L}.
  Assumes that they don't exist."""

  for pipe_name in L:
    stderr.write("creating pipe %s\n" % pipe_name)
    os.mkfifo(pipe_name)
# ----------------------------------------------------------------------  

def terminate_process(ok):
  """Terminates the process with exit status 0 if {ok} is true,
  status 1 if {ok} is false."""
  
  if ok:
    stderr.write("[muff_capture:] done.\n")
    sys.exit(0)
  else:
    stderr.write("** [muff_capture:] process aborted.\n")
    sys.exit(1)
  assert False # Never gets here.
# ----------------------------------------------------------------------

main()
