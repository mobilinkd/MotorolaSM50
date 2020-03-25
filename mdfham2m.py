#!/usr/bin/env python3

# Copyright 2020 Mobilinkd LLC. Released under terms of the GNU GPL V3.

"""
This program is designed to change the band limits of the Motorola SM50
RSS program to include the 2m VHF ham band.  It lowers the band range
from 150-170MHz to 144-164MHz.  This only modifies the MDF.  It makes
no changes to the radio.
"""

import struct
import shutil
import tempfile
import sys
import os


def checksum(buffer):
    """Calculate a simple checksum by adding all of the bytes as unsigned
    values and returning the result modulo 2^16 (65536).
    """
    
    cksum = 0
    for val in struct.iter_unpack('B', buffer):
        cksum += val[0]
    return cksum & 0xFFFF

def replace_band_limits(buffer):
    """Move the band range down 6MHz so that it starts at 144MHz.  This
    could also be used to restrict the RSS to the 2m ham band (144-148MHz),
    by replacing the value with b'\xA0\x05\xC8\x05' but the alignment
    functions would still TX outside of these bands.
    """

    # Replace the band range 150-170Mhz with 144-164MHz
    return buffer.replace(b'\xDC\x05\xA4\x06', b'\xA0\x05\x68\x06', 3)

def fixup_checksum(buffer, original_checksum):
    """ Fix up the MDF file so that the checksum matches the original.
    SM50.EXE will not allow changes to the codeplugs when there is a
    checksum mismatch.
    
    To make the checksum match, we update some of the text in the
    copyright message embedded in the MDF file.
    """

    new_checksum = checksum(buffer)
    difference = original_checksum - new_checksum
    
    print("Updating file to make up checksum difference of {}".format(difference))

    # When difference is positive, we need to add bits to the data,
    # otherwise we need to remove them.  The number of bits should
    # be relatively small.
    
    original = b'ALL RIGHTS RESERVED'
    replaced = bytearray(original)
    for i in range(len(replaced)):
        if difference == 0: break
        if replaced[i] == 32: continue
        if difference > 0:
            change = min(32, difference)
        else:
            change = max(-32, difference)
        replaced[i] += change
        difference -= change
    
    print('Replacing {} with {} in MDF.'.format(original, bytes(replaced)))          
    
    return buffer.replace(original, replaced, 1)

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("usage: {} <filename>".format(sys.argv[0]))
        sys.exit(1)

    # Verify that the input file exists or fail gracefully.
    filename = os.path.abspath(sys.argv[1])
    if not os.path.exists(filename):
        print('"{}" does not exist'.format(filename))
        sys.exit(2)
    
    # Read the original file and checksum.
    buffer = open(filename, 'rb').read()
    original_checksum = checksum(buffer)
    print('Original checksum = {:04X}'.format(original_checksum))
    
    # Update the band limits and fix up the checksum.
    updated_buffer = replace_band_limits(buffer)
    fixed_buffer = fixup_checksum(updated_buffer, original_checksum)
    new_checksum = checksum(fixed_buffer)
    print('New checksum = {:04X}'.format(new_checksum))
    
    # Verify the checksum was properly updated before modifying files.
    if new_checksum != original_checksum:
        print("Could not update the checksums to match. Aborting.")
        sys.exit(3)
    
    # Create a temp file in the proper directory and write the new MDF to it.
    new_file = tempfile.NamedTemporaryFile(dir=os.path.dirname(filename), delete=False)
    new_file.write(fixed_buffer)

    backup_filename = filename + '.BAK'
    
    print("Renaming {} to {}".format(filename, backup_filename))
    os.rename(filename, backup_filename)
    print("Renaming temp file to {}".format(filename))
    os.rename(new_file.name, filename)
    print("Done.")
            
