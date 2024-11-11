#! /usr/bin/python3
# Last edited on 2018-09-04 18:43:27 by stolfilocal

# {muff_arduino.py}: Library module for interfacing with the
# Arduino controller of the MUFF v2.0 microscope positioner.

import os, sys, serial, time
from sys import stderr 

num_LEDs = 24     # Number of LEDs; named 'A', 'B', etc.
verbose = False   # If true, prints lots of debugging info.

# GENERAL OBSERVATIONS

# Most functions in this module take a {sport} argument
# which is the serial port object connected to the Arduino.

# If {sport = None}, the functions just pretend that 
# the Arduino is there and responding with '0's as expected.
# This is useful when debugging this module and the 
# Arduino is not available.

def connect(arduino_present,verb):
  """Open a serial port to the Arduino and returns it.
  
  However, if {arduino_present} is false, skips and returns {None}
  instead.
  
  If {verb} is true, turns on verbose mode for all functions in
  this module."""
  
  global verbose
  verbose = verb
  if not arduino_present:
    stderr.write("[muff_arduino:] !! debugging run (without the Arduino)\n")
    return None
  else:
    sport = serial.Serial \
      ( "/dev/ttyUSB0", 9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE )
    time.sleep(2)
    return sport
# ----------------------------------------------------------------------

# COMMANDS FOR THE MUFF POSITIONER FIRMWARE
  
def start_motor(sport,dir,fast):
  """Send command to the Arduino to start moving the microscope 
  in the direction {dir} (+1 = up, -1 = down).  If the boolean {fast} is
  true, set the high max speed (fast, coarse), else uses the low max speed (slow, fine).
  Waits for a '0' response from the Arduino, which should come while the motor 
  is still moving."""
  
  global verbose
  
  # IN case the motor is moving, stop it:
  stop_motor(sport)
  
  if verbose: 
    stderr.write("[muff_arduino:] starting motor in direction %+d" % dir)
  
  # Choose the command to send to the Arduino:
  if dir == +1:
    if fast:
      command = b"6" # Start moving up, fast.
    else:
      command = b"1" # Start moving up, slow.
  elif dir == -1:
    if fast:
      command = b"7" # Start moving down, fast.
    else:
      command = b"2" # Start moving down, slow.
  else:
    assert False

  # Send the command:
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------
  
def stop_motor(sport):
  """Send command to the Arduino to stop the motor, in case it is moving
  because of a previous {start_motor}.  Waits for the 
  Arduino to respond with '0'."""
  
  global verbose
  
  if verbose: stderr.write("[muff_arduino:] stopping motor\n")

  # Choose and send the Arduino command:
  command = b"3"
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------
  
def set_Z_step(sport,Z_step):
  """Send command to the Arduino to define the Z increment
  to be {Z_step} millimeters.  Waits for the Arduino
  to respond with '0'."""
  
  global verbose
  
  # Convert the given {Z_step} to integer microns in {-999} tp {+999}:
  istep = int(round(Z_step*1000)) # Step size in microns.
  assert (istep >= -999) and (istep <= +999) # Arduino expects sign and 3 digits.
  
  if verbose: stderr.write("[muff_arduino:] defining Z step to be %+03d microns\n" % istep)
  
  # Construct and send the Arduino command:
  command = ("4%+03d" % istep).encode('ascii');
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------
  
def move_microscope(sport):
  """Sends commands to the Arduino to raises the microscope 
  holder by the predefined Z step amount. Waits for
  the Arduino to respond with '0'."""
  
  global verbose
  
  if verbose: stderr.write("[muff_arduino:] raising microscope by 1 step\n")
  
  # Construct and send the Arduino command:
  command = b'5'
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------

def test_lights(sport):
  """Tests the LEDs by turning them all on, then
  turning them all off.  Waits for the 
  Arduino to respond with '0' after each order."""
  
  global verbose
  
  if verbose: stderr.write("[muff_arduino:] testing the LEDs\n")
  
  switch_all_LEDs(sport,1.0)
  time.sleep(1.0)
  switch_all_LEDs(sport,0.0)
  time.sleep(0.1)
# ----------------------------------------------------------------------
 
def switch_LED(sport,lix,pwr):
  """Sends commands to the Arduino to turn the LED number {lix} on 
  with relative intensity {pwr}, which should be between 0.0 
  (off) and 1.0 (max intensity).  Waits for the 
  Arduino to respond with '0'.
  
  Currently only works if {pwr} is 0 (Arduino command '-')
  or 1 (Arduino command '+').""" 
  
  global verbose
  
  if verbose: stderr.write("[muff_arduino:] setting LED %02d intensity to %.2f\n" % (lix,pwr))
    
  assert type(lix) is int and lix >= 0 and lix < num_LEDs
  assert type(pwr) is float and pwr >= 0.0 and pwr <= 1.0
  
  # Select the opcode of the Arduino LED switching command:
  if pwr == 1.0:
    opcode = "+"
  elif pwr == 0.0:
    opcode = "-"
  else:
    stderr.write("** [muff_arduino:] partial LED intensity not implemented yet.\n")
    sys.exit(1)
    
  # Convert LED index {0,1,...} to LED name 'A','B',...:
  lname = chr(ord("A") + lix)

  # Compose and send the Arduino command:
  command = (opcode + lname).encode('ascii')
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------
 
def switch_all_LEDs(sport,pwr):
  """Sends commands to the Arduino to turn all LEDs number on 
  with relative intensity {pwr}, which should be between 0.0 
  (off) and 1.0 (max intensity).  Waits for the 
  Arduino to respond with '0'.
  
  Currently only works if {pwr} is 0 (Arduino command '-@')
  or 1 (Arduino command '+@').""" 
  
  global verbose

  if verbose: stderr.write("[muff_arduino:] seting intensity of all LEDs to %.2f\n" % pwr)

  assert type(pwr) is float and pwr >= 0.0 and pwr <= 1.0
  
  # Choose and send the Arduino command:
  if pwr == 1.0:
    command = b'+@';
  elif pwr == 0.0:
    command = b'-@';
  else:
    stderr.write("** [muff_arduino:] partial LED intensity not implemented yet.\n")
    sys.exit(1)
  send_command_and_wait(sport, command)
# ----------------------------------------------------------------------

# LOW_LEVEL FUNCTIONS

def send_command_and_wait(sport, command):
  """Sends the byte sequence {command} to the Arduino through the 
  serial port object {sport}, after discarding any 
  unread input bytes.  Waits for the Arduino to 
  reply with '0' byte.
  
  However, if {sport} is {None}, writes the bytes to {stderr} 
  instead, and returns without waiting."""
  
  send_command(sport, command)
  wait_arduino_OK(sport)
# ----------------------------------------------------------------------

def send_command(sport, command):
  """Sends the bytes {command} to the Arduino through the 
  serial port object {sport}, after discarding any unread 
  input bytes.  Does NOT wait for a response from the Arduino.
  
  However, if {sport} is {None}, writes the bytes to {stderr} 
  instead, and returns."""
  
  if sport == None:
    stderr.write("[muff_arduino:] would send to Arduino: '%s'\n" % show_bytes(command,False))
  else:
    if verbose: stderr.write("[muff_arduino:] sending to Arduino: '%s'\n" % show_bytes(command,False))
    sport.flush()
    sport.write(command)
# ----------------------------------------------------------------------

def wait_arduino_OK(sport):
  """Waits for a b'0' command return code from the serial 
  port {sport}.
  
  Ignores spaces and EOLs (NL, CR). If it receives a "#", ignores 
  everything up to and including the EOL. Otherwise, if the return 
  code is not "0", aborts with error.
  
  If {sport} is {None} (debugging mode), does not try to read, 
  and returns immediately."""
  
  if sport == None: 
    time.sleep(0.2)
    stderr.write("[muff_arduino:] pretending that the Arduino replied OK\n")
    return
  else:
    c = read_signif(sport)
    if c != b'0':
      stderr.write("** [muff_arduino:] Invalid OK return code from Arduino: '%s'\n" % show_bytes(c,True))
      sys.exit(1)
# ----------------------------------------------------------------------

def read_signif(sport):
  """Reads one character from the serial port object {sport} (which
  should not be {None}), skipping blanks, end-of-lines (CR, NL)
  and comments (from '#' to end-of-line).  
  If {verbose} is true, echoes the character on {stderr}. 
  Returns the character as a {bytes} object.  
  
  Complains and aborts if the read fails."""
  
  assert sport != None

  # Skip any unread characters:
  sport.flush()
  
  # Read until non-blank and non-comment, or error:
  while True:
    c = readchar(sport)
    if c == b'#':
      if verbose: stderr.write("[muff_arduino:] received from Arduino: '%s" % show_bytes(c,False));
      # Skip all data to end-of-line, echo on {stderr}:
      skip_to_eol(sport)
      if verbose: stderr.write("'\n")
    else:
      if verbose: stderr.write("[muff_arduino:] received from Arduino: '%s'\n" % show_bytes(c,True))
      if c != b' ' and c != b'\r' and c != b'\n':
        break
      else:
        # Ignore.
        pass
  return c
# ----------------------------------------------------------------------

def skip_to_eol(sport):
  """Reads characters from the serial port {sport} (which must not
  be {None}) until the first end-of-line (CR or NL), echoing 
  them on {stderr} if {verbose} is true."""
  
  assert sport != None

  while True:
    c = readchar(sport);
    if verbose: stderr.write(show_bytes(c,False))
    if c == b'\r' or c == b'\n':
      break
# ----------------------------------------------------------------------

def readchar(sport):
  """Reads one character from the serial port {sport} (which must not
  be {None}) and returns it as a {bytes} object. Complains and aborts 
  if the port yielded empty or more than 1 character.  Otherwise does 
  NOT echo the character on {stderr}, even if {verbose} is true."""
  
  assert sport != None
  
  while True:
    c = sport.read() # Returns a {bytes} object.
    if len(c) == 1:
      return c
    else:
      sys.stderr.write("\n[muff_arduino] ** sport.read() returned '%s' (len = %d)\n" % (show_chrs(c,False), len(c)));
      sys.stderr.write("\n[muff_arduino] ** aborted.\n")
# ----------------------------------------------------------------------

def show_bytes(s, blanks):
  """Given a {bytes} object {s}, returns a {string} object
  with each non-printing char in {s} replaced by '[chr({NNN})]',
  where {NNN} is the character's decimal {ord}.  Also replaces 
  quotes, brackets, parentheses. If {blanks} is true, 
  replaces blanks too."""
  
  n = len(s)
  res = ""
  bad = b"\'\"[]()" # Printable bytes that should be converted too.
  for i in range(n):
    c = s[i]
    if (c == b' '[0] and blanks) or (c < b' '[0]) or (c > b'~'[0]) or (c in bad):
      # Show chr code:
      res = res + ("[chr(%03d)]" % c)
    else:
      res = res + chr(c)
  return res
# ----------------------------------------------------------------------

