#!/usr/bin/env python3

# /************
#  * 
#  * Copyright 2019 by Fernando Trias. All rights reserved.
#  * 
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
#  * and associated documentation files (the "Software"), to deal in the Software without restriction,
#  * including without limitation the rights to use, copy, modify, merge, publish, distribute,
#  * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
#  * furnished to do so, subject to the following conditions:
#  *
#  * The above copyright notice and this permission notice shall be included in all copies or
#  * substantial portions of the Software.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
#  * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#  * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#  *
#  ************/

import binascii
import argparse
import os
import sys
import time

class colors:
    black = '\033[0;30m'
    white = '\033[1;37m'
    dark_gray = '\033[1;30m'
    light_gray = '\033[0;37m'
    red = '\033[0;31m'
    light_red = '\033[1;31m'
    green = '\033[0;32m'
    light_green = '\033[1;32m'
    blue = '\033[0;34m'
    light_blue = '\033[1;34m'
    purple = '\033[0;35m'
    light_purple = '\033[1;35m'
    cyan = '\033[0;36m'
    light_cyan = '\033[1;36m'
    orange = '\033[0;33m'
    yellow = '\033[1;33m'
    no_color = '\033[0m'

# ---------------------------------------------------------------------------- #
#                                    OPTIONS                                   #
# ---------------------------------------------------------------------------- #
# -------------------------------- FILE PATHS -------------------------------- #
gprof_path = "/usr/bin/arm-none-eabi-gprof"
elf_path="/tmp/build.elf"

# --------------------------------- ARGUMENTS -------------------------------- #
save_img = False
img_name = ''

save_file = False
file_name = ''

save_project = False
project_name = ''

function_exclude_opt = '--no-time='
function_excludes = ['gprof_systick_isr', '_stext', '__gnu_mcount_nc', '_mcount_internal', 'systick_isr']
function_excludes_str = ''

# ---------------------------------------------------------------------------- #
#                                     GPROF                                    #
# ---------------------------------------------------------------------------- #
def call_gprof():
    if save_file:
        print(f"Generating file output from gmon.out...")
        os.system(f"gprof {elf_path} {function_excludes_str} > ./{file_name}.txt")
        print(f"\t{colors.light_green}COMPLETE")
    if save_img:
        print(f"Generating image output from gmon.out...")
        os.system(f"gprof {elf_path} {function_excludes_str} | gprof2dot | dot -Tpng -o {img_name}.png")
        print(f"\t{colors.light_green}COMPLETE")
    if save_project:
        print(f"Generating project output from gmon.out...")
        os.system(f"mkdir -p ./{project_name}")
        os.system(f"gprof {elf_path} {function_excludes_str} | gprof2dot | dot -Tpng -o ./{project_name}/{project_name}.png")
        os.system(f"gprof {elf_path} {function_excludes_str} > ./{project_name}/{project_name}.txt")
        print(f"\t{colors.light_green}COMPLETE")
        
    if not save_file and not save_img and not save_project:
        os.system(f"gprof {elf_path} {function_excludes_str}")
    
    exit(0)

 # ---------------------------------------------------------------------------- #
 #                              HEX ASCII ENCODING                              #
 # ---------------------------------------------------------------------------- #
def process_hex(filename, outfile="gmon.out"):
    with open(filename) as inf:
        with open(outfile, "wb") as outf:
            for line in inf:
                line = line.strip()
                if line == "END": break
                if line[0] == "S" or line[0] == "E": continue
                outf.write(binascii.a2b_hex(line))
    call_gprof()

# ---------------------------------------------------------------------------- #
#                            SERIAL BINARY ENCODING                            #
# ---------------------------------------------------------------------------- #
def process_msg(fxn, n, s):
    global fp
    global ser
    if fxn == 1:  # open
        (fmode, fname) = s.decode('ascii').split(":", 2)
        fp = open(fname, fmode)
        print("open %s" % fname)
    elif fxn == 2:  # close
        fp.close()
        print("close")
        call_gprof()
    elif fxn == 4:  # write
        fp.write(s)

def filehost():
    global ser
    fxn = os.read(ser, 1)  # function
    fxn = ord(fxn)
    n = os.read(ser, 1)  # length
    n = ord(n)
    if n == 0: return
    s = os.read(ser, n)  # data
    process_msg(fxn, n, s)

def process_serial(file):
    global ser
    while True:
        if not os.path.exists(file):
            print("waiting for path:", file)
            while not os.path.exists(file):
                time.sleep(0.1)
        print("Opened serial %s" % file)
        ser = os.open(file, os.O_RDWR)
        while True:
            try:
                c = os.read(ser, 1)
            except OSError:
                break
            if len(c) > 0:
                if ord(c) == 1:  # control
                    filehost()
                else:
                    sys.stdout.write(c.decode('ascii'))
        print("Close serial %s" % file)

# ---------------------------------------------------------------------------- #
#                                     MAIN                                     #
# ---------------------------------------------------------------------------- #
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse gmon.out file from Teensy and run gprof.')
    parser.add_argument('--hex', help='Convert from ascii hex')
    parser.add_argument('--serial', help='Read serial device codes')
    parser.add_argument('--elf', help='ELF file to read')
    parser.add_argument('--img', help='Generate an image from the gmon.out')
    parser.add_argument('--save', help='Save gprof output to a text file')
    parser.add_argument('--project', help='Save gprof output to text file and image file in a folder with the given name')
    parser.add_argument('--exclude', help='Excludes the given function names from the gprof output, separate functions by a space and enclose them all in quotations (EX: --exclude "func1 func2 func3")')

    args = parser.parse_args()

    if args.elf:
        elf_path = args.elf
        print(f'{colors.no_color}ELF path:\t{elf_path}')

    # ------------------------------ SAVE ARGUMENTS ------------------------------ #
    print(f"{colors.no_color}Image output:\t", end = '')
    if args.img is not None:
        save_img = True
        img_name = args.img
        print(f"{colors.light_green}ENABLED")
        print(f"{colors.no_color}Image name:\t{colors.light_cyan}{img_name}")
    else:
        print(f"{colors.red}DISABLED")
    
    print(f"{colors.no_color}File output:\t", end = '')
    if args.save is not None:
        save_file = True
        file_name = args.save
        print(f"{colors.light_green}ENABLED")
        print(f"{colors.no_color}File name:\t{colors.light_cyan}{file_name}")
    else:
        print(f"{colors.red}DISABLED")
    
    print(f"{colors.no_color}Project output:\t", end = '')
    if args.project is not None:
        save_project = True
        project_name = args.project
        print(f"{colors.light_green}ENABLED")
        print(f"{colors.no_color}Project name:\t{colors.light_cyan}{project_name}")
    else:
        print(f"{colors.red}DISABLED")

    # --------------------------- PROCESSING ARGUMENTS --------------------------- #
    if args.hex is not None:
        print(f"{colors.no_color}Processsing {colors.light_purple}HEX")
        process_hex(args.hex)
    elif args.serial is not None:
        print(f"{colors.no_color}Processsing {colors.light_purple}SERIAL")
        process_serial(args.serial)
    else:
        print(f"{colors.red}ERROR: NO ARGUMENTS")

    # ------------------------------- MAKE EXCLUDES ------------------------------ #
    if args.exclude is not None:
        for func_name in args.exclude.split(' '):
            function_excludes.append(func_name.strip())
    
    function_excludes_str = ''.join([f"{function_exclude_opt}{func_name} " for func_name in function_excludes]).strip()
