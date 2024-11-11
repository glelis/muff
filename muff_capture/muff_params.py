#! /usr/bin/python3
# Last edited on 2018-07-13 23:41:59 by stolfilocal

# {muff_params.py}: Library module for obtaining and saving 
# scanset parameters.

import os, sys, re
from sys import stderr 

# Global constants for parameter verification:
nL_max = 24
nV_max = 1
nH_max = 99
Z_step_max = 0.999
Z_step_min = -Z_step_max

verbose = False  # If true, prints debugging info.

def get_from_user():
  """Asks the user to enter {nL,nV,nH,Z_step} through {stdin}
  and returns a dictionary with the parameters.  Returns {None}
  in case of error."""

  params = {}
  try:
    nL_prompt = "number of lights (1 to %d)? " % nL_max
    params["nL"] = parse_int(input(nL_prompt),"nL",False,1,nL_max)
    params["nV"] = 1 # For now.
    nH_prompt = "number of focus planes (1 to %d)? " % nH_max
    params["nH"] = parse_int(input(nH_prompt),"nH",False,1,nH_max)
    Z_step_prompt = "displacement between focus planes in mm (%+5.3f to %+5.3f)? " % ( Z_step_min, Z_step_max )
    params["Z_step"] = parse_float(input(Z_step_prompt),"Z_step",False,Z_step_min,Z_step_max)
  except:
    stderr.write("** [muff_params:] some error getting parameters from user\n")
    return None

  return params
# ----------------------------------------------------------------------  
      
def read_from_named_file(fname):
  """Reads the parameters {nL,nV,nH,Z_step} from file {fname},
  one per line, and returns a tuple with the parameters.  
  Returns {None} in case of error."""

  # Open the file:
  try:
    rd = open(fname, 'r')
  except:
    stderr.write("** [muff_params:] failed to open file '%s'\n" % fname)
    return None
    
  # Parse the parameters:
  params = {}
  try:
    params["nL"] = parse_int(read_signif_line(rd),"nL",True,1,nL_max)
    params["nV"] = parse_int(read_signif_line(rd),"nV",True,1,1)
    params["nH"] = parse_int(read_signif_line(rd),"nH",True,1,nH_max)
    params["Z_step"] = parse_float(read_signif_line(rd),"Z_step",True,Z_step_min,Z_step_max)
  except:
    stderr.write("** [muff_params:] some error reading parameters from '%s'\n" % fname)
    return None

  rd.close()  
  return params
# ---------------------------------------------------------------------- 

def read_signif_line(rd):
  """Tries to from file {rd} a line. If it succeeds, strips any trailing '#'
  comments (but leaves the end-of-line). Keeps repeating this until the 
  result is not a blank line. If runs into EOF, returns an empty string."""
  
  while True:
    s = rd.readline()
    if s == "": return s
    re.sub(r'[#].*$', '', s)
    s = s.strip()
    if s != "": return s
  assert False # Can't get here.
# ---------------------------------------------------------------------- 
  
def parse_int(s,name,tagged,lo,hi):
  """Converts the string {s} to an integer, which must be in the range {lo..hi}.
  If {tagged} is true, requires "{name} = " in front of the parameter value.
  Raises an exception in case of error."""
  
  s = preparse(s,name,tagged)
  
  try:
    val = int(s)
  except:
    stderr.write("** [muff_params:] parameter {%s} = '%s' is invalid\n" % (name, s))
    raise ValueError

  # Check range:
  if val < lo or val > hi:
    stderr.write("** [muff_params:] parameter {%s} = %d should be in %d..%d\n" % (name, val, lo, hi))
    raise ValueError
    
  if verbose: stderr.write("[muff_params:] parameter {%s}: parsed to %d\n" % (name, val))
  return val
# ----------------------------------------------------------------------  

def parse_float(s,name,tagged,lo,hi):
  """Converts the string {s} to a float, which must be in the range {lo..hi}.
  If {tagged} is true, requires "{name} = " in front of the parameter value.
  Raises an exception in case of error."""
  
  s = preparse(s,name,tagged)
  
  # Parse the string:
  try:
    val = float(s)
  except:
    stderr.write("** [muff_params:] parameter {%s} = '%s' is invalid\n" % (name, s))
    raise ValueError
    
  # Check range:
  if val < lo or val > hi:
    stderr.write("** [muff_params:] parameter {%s} = %d should be in %+f..%+f\n" % (name, val, lo, hi))
    raise ValueError

  if verbose: stderr.write("[muff_params:] parameter {%s}: parsed to %+f\n" % (name, val))
  return val
# ----------------------------------------------------------------------  

def preparse(s,name,tagged):
  """Removes spurious whitespace from the string {s}, which must be non-empty.
  If {tagged} is true, requires "{name} = " in front of the parameter value.
  Raises an exception in case of error."""
  
  # Remove spurious whitespace:
  s = s.strip()
  if verbose: stderr.write("[muff_params:] parameter {%s}: got '%s'\n" % (name, s))
    
  if s == "":
    stderr.write("** [muff_params:] parameter {%s} is empty\n" % name)
    raise ValueError

  if tagged:
    # Require and remove tag:
    L = re.split(r'([ ]*[=][ ]*)', s)
    if verbose: stderr.write("[muff_params:] split to ['%s']\n" % "' '".join(L))
    if len(L) != 3 or L[0] != name or L[1].strip() != '=':
      stderr.write("** [muff_params:] '%s' sould be '%s = {VALUE}'\n" % (name, name))
      raise ValueError
    else:
      s = L[2]
      if verbose: stderr.write("[muff_params:] retained '%s'\n" % s)
    
  return s
# ----------------------------------------------------------------------  

def check_for_help(HELP, INFO):
  """If the user so requested, print the full
  help text, and exit."""
  
  if len(sys.argv) == 2 and sys.argv[1] == "-help":
    stderr.write("SYNOPSIS\n")
    stderr.write(HELP + "\n\n")
    stderr.write("DESCRIPTION\n")
    stderr.write(INFO + "\n")
    exit(0)
# ----------------------------------------------------------------------  


