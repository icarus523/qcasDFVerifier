# epsig2_gui.py 
# Ported from Rob Larkin's LUA script version to python. 
# 
##	from Rob's original epsig2.lua 
##  Usage:
##		lua epsig2.lua bnkfilename [seed [reverse] ]
##
##	examples: 	lua epsig2.lua ARI\10163088_F23B_6040_1.bnk
##				lua epsig2.lua ARI\10163088_F23B_6040_1.bnk 1234
##				lua epsig2.lua ARI\10163088_F23B_6040_1.bnk 00 reverse
##      If no seed supplied then a seed of 00 is used
##
##	Note wrt a Casino "reverse"'d result, the result wrt Casino datafiles is the last 8 chars of the result displayed. E.g.
##	Result: 3371cc5638d735cefde5fb8da904ac8d54c2050c the result is 54c2050c

# Version History
# v1.0 - Initial Release
# v1.1 - Add support to SL1 datafile seed files via combobox and file chooser widget, updated GUI
# v1.2 - Add support to use MSL (QCAS) files and automatically flip the SEED as expected for completing CHK01 (Yick's request) 

import os
import sys
import csv
import hashlib
import hmac
import binascii
import struct
import array
import datetime
import string

from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from threading import Thread

class epsig2:

    # input: file to be CRC32 
    def dohash_crc32(self, fname):
        buf = open(fname,'rb').read()
        buf = (binascii.crc32(buf) & 0xFFFFFFFF)

        return "%08X" % buf

    # input: file to be hashed using sha1()
    # output: hexdigest of input file    
    def dohash_sha1(self, fname, chunksize=8192): 
        m = hashlib.sha1()         

        # Read in chunksize blocks at a time
        with open(fname, 'rb') as f:
            while True:
                block = f.read(chunksize)
                if not block: break
                m.update(block)    

        return m.hexdigest()

    # input: file to be hashed using hmac-sha1
    # output: hexdigest of input file    
    def dohash_hmac(self, fname, chunksize=8192):
            key = bytes.fromhex(self.seed)
            m = hmac.new(key, digestmod = hashlib.sha1)

            # Read in chunksize blocks at a time
            with open(fname, 'rb') as f:
                while True:
                    block = f.read(chunksize)
                    if not block: break
                    m.update(block)      
            return m.hexdigest()
    
    def checkhexchars(self, text):
        return (all(c in string.hexdigits for c in text))    

    def dobnk(self, blocksize):
        oh = "0000000000000000000000000000000000000000"
        # Verify Seed is a number String format, and atleast 2 digits long 
        if (len(self.seed) < 2 or not self.checkhexchars(self.seed)):
            messagebox.showerror("Error in Seed Input", "Expected atleast two Hexadecimal characters as the Seed input" +
                                 ".\n\nCheck your Seed string again: " + self.seed)
            return -1
        else:
            try:
                self.text_BNKoutput.insert(END, "Processing: " + self.mandir + "/" + self.bnk_filename + "\n")
                infile = open(self.mandir + "/" + self.bnk_filename, 'r')
                fdname = ['fname', 'type', 'blah']
                reader = csv.DictReader(infile, delimiter=' ', fieldnames = fdname)

                self.text_BNKoutput.insert(END, "Seed: " + self.seed + "\n")
            
                for row in reader:
                    if row['type'].upper() == 'SHA1':
                        # check if the file exists
                        if (os.path.isfile(self.mandir + "/" + row['fname'])):
                            localhash = self.dohash_hmac(self.mandir + "/" + str(row['fname']), blocksize)

                            self.resulthash = localhash
                            # handle incorrect seed length
                            if localhash == 0:
                                break # exit out cleanly
                        
                            # include a space for every eight chars
                            if (self.eightchar.get() == 1):
                                eightchar_displaytext = self.insert_spaces(str(localhash), 8)
                            else:
                                eightchar_displaytext = str(localhash)

                            if self.uppercase.get() == 0:
                                self.text_BNKoutput.insert(END, eightchar_displaytext + " " + str(row['fname']) + "\n")
                            else:
                                self.text_BNKoutput.insert(END, eightchar_displaytext.upper() + " " + str(row['fname']) + "\n")

                            # XOR strings, by first converting to numbers using int(), and providing expected base (16 for hex numbers)
                            # Then two conversions, to perform the XOR operator "^" then convert back to hex
                            oh = hex(int(oh,16) ^ int(str(localhash), 16))
                            #print (oh.zfill(40) + "\t" + str(row['fname']))
                            print (str(localhash) + "\t" + str(row['fname']))
                        else: 
                            self.text_BNKoutput.insert(END, "could not read file: " + str(row['fname']) + "\n")
                    else: 
                        messagebox.showerror("Not Yet Implemented!", "Unsupported hash algorithm: " + row['type'].upper() + ".\n\nExiting. Sorry!")
                        sys.exit('Unsupported hash algorithm: ' + row['type'])
                        # Need to implement CR16, CR32, PS32, PS16, OA4F and OA4R

            except csv.Error() as e:
                messagebox.showerror("CSV Parsing Error", "Malformed BNK entry, check the file manually" + row['type'].upper() + ".\n\nExiting.")
                sys.exit('file %s, line %d: %s' % (filename, reader.line_num, e))
            
        return oh
    
    # Inserts spaces on [text] for every [s_range]
    def insert_spaces(self, text, s_range):
        return " ".join(text[i:i+s_range] for i in range(0, len(text), s_range))

    def processfile(self, chunks):
        h = self.dobnk(chunks)
        
        if h == -1: 
            return # handle error in seed input
        else:
            self.text_BNKoutput.insert(END, "RAW output: " + str(h).zfill(40) + "\n")

            #strip 0x first
            tmpStr = str(h).lstrip('0X').zfill(40) # forces 40 characters with starting 0 characters. 
            tmpStr = str(h).lstrip('0x').zfill(40)

            # include a space for every eight chars
            if (self.eightchar.get() == 1):
                eightchar_displaytext = self.insert_spaces(tmpStr, 8)
            else: 
                eightchar_displaytext = tmpStr

            # Do QCAS expected result       
            if (self.reverse.get() == 1):
                if self.uppercase.get() == 1:
                    displaystr = self.getQCAS_Expected_output(eightchar_displaytext)
                    self.text_BNKoutput.insert(END, "QCAS Expected Result: " + displaystr.upper())
                else:
                    displaystr = self.getQCAS_Expected_output(eightchar_displaytext)
                    self.text_BNKoutput.insert(END, "QCAS Expected Result: " + displaystr) # Slice characters from the 8th-last position to the end
            # Normal XOR result
            elif (self.reverse.get() == 0): 
                if self.uppercase.get() == 1:
                    self.text_BNKoutput.insert(END, "XOR: " + eightchar_displaytext.upper())
                else:
                    self.text_BNKoutput.insert(END, "XOR: " + eightchar_displaytext)
            else:
                messagebox.showerror("Checkbox Error", "Unknown state")
                   
            self.text_BNKoutput.insert(END, "\n\n")

    def getQCAS_Expected_output(self, text):
        tmpstr = text[:8] # Returns from the beginning to position 8 of uppercase text
        return "".join(reversed([tmpstr[i:i+2] for i in range(0, len(tmpstr), 2)]))
    
    def processdirectory(self):
        print("Arg 1 is a path")

    def handleButtonPress(self, myButtonPress):
        if myButtonPress == '__selected_bnk_file__':
            if (os.name == 'nt'): # Windows OS
                tmp = filedialog.askopenfile(initialdir='G:\OLGR-TECHSERV\BINIMAGE')
            elif (os.name == 'posix'): # Linux OS
                tmp = filedialog.askopenfile(initialdir='.')
            else: 
                tmp = filedialog.askopenfile(initialdir='.')

            if tmp:
                self.bnk_filepath = tmp.name
                self.bnk_filename = os.path.basename(self.bnk_filepath)
                self.textfield_SelectedBNK.delete(0, END)
                self.textfield_SelectedBNK.insert(0, self.bnk_filepath)

        elif myButtonPress == '__start__':
            self.bnk_filepath = str(self.textfield_SelectedBNK.get())
            if (os.path.isfile(self.bnk_filepath)):                 
                if self.bnk_filename == '': 
                    self.bnk_filename = os.path.basename(self.bnk_filepath)
                    
                self.mandir = os.path.dirname(self.bnk_filepath)

                if (self.reverse.get() == 1): # reverse the seed.
                    self.seed = self.getQCAS_Expected_output(self.combobox_SelectSeed.get())
                else: 
                    self.seed = self.combobox_SelectSeed.get()

                print("Self.Seed is: " + self.seed)
                
                self.processfile(8192)     

            else:
                messagebox.showerror("Files not Chosen!", "Please select files first")

        elif myButtonPress == '__clear__':
                self.text_BNKoutput.delete(1.0, END)
                self.cb_reverse.deselect()
                self.bnk_filepath = ''
                self.bnk_filename = ''
                self.textfield_SelectedBNK.delete(0, END)
                self.reverse.set(0)
                self.mslcheck.set(0)
                self.cb_uppercase.deselect()
                self.cb_mslcheck.deselect()
                self.uppercase.set(0)
                self.eightchar.set(0)
                self.cb_eightchar.deselect()
                self.label_SeedPath.configure(text="Not Using SL1 file") 
                self.combobox_SelectSeed.set('0000000000000000000000000000000000000000')
                self.combobox_SelectSeed['values'] = ()
                        
        elif myButtonPress == '__selected_seed_file__':
            if (os.name == 'nt'): # Windows OS
                if (self.mslcheck.get() == 1): # Handle MSL file option for QCAS datafiles
                    tmp = filedialog.askopenfile(initialdir='G:\OLGR-TECHSERV\MISC\BINIMAGE\qcas')
                else: 
                    tmp = filedialog.askopenfile(initialdir='S:\cogsp\docs\data_req\download\master') # put S:\ dir here. 
            elif (os.name == 'posix'): # Linux OS (my dev box)
                tmp = filedialog.askopenfile(initialdir='.')
            else: 
                tmp = filedialog.askopenfile(initialdir='.')
                
            if tmp: # Selected something
                self.seed_filepath = tmp.name
                self.getComboBoxValues(self.seed_filepath)
                
                # Generate Year and Date based on numbers extracted
                sl1date = datetime.datetime.strptime(self.sl1_year + "/" + self.sl1_month, "%Y/%m")
                self.label_SeedPath.configure(text="Seed File: " + sl1date.strftime("(%b %Y)") + ": " + self.seed_filepath) 

    def processsl1file(self, fname): 
        seedlist = ()
        with open(fname,'r') as sl1file:
            sl1entry = csv.reader(sl1file, delimiter=',')
            try:
                # Select the Columns we want - index starts at 0
                included_cols = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]
                for row in sl1entry:
                    seedlist = list(row[i] for i in included_cols) # create a list with only the columns we need
                    self.sl1_year = row[0] # extract year
                    self.sl1_month = row[1] # extract month
            except csv.Error as e:
                sys.exit('file %s, line %d: %s' % (fname, sl1file.line_num, e))
        return seedlist      

    def getComboBoxValues(self, fname):
        if (os.path.isfile(fname)):
            self.combobox_SelectSeed['values'] = self.processsl1file(fname)
        else:
            messagebox.showerror("Expected SL1 or MSL file to Process", fname + " is not a valid seed file")
            sys.exit(1)                 

    def setupGUI(self):
        self.root.wm_title("epsig2 BNK file v1.2")
        self.root.resizable(0,0)
        
        frame_toparea = ttk.Frame(self.root)
        frame_toparea.pack(side = "top", fill="both", expand=True)
        frame_toparea.config(relief = RIDGE, borderwidth = 0)
        
        ttk.Label(frame_toparea, justify=LEFT,
                  text = 'GUI script to process BNK files. Note: Supports only HMAC-SHA1').grid(row = 0, columnspan=4, padx=3, pady=3)

        # Button Selected BNK file
        button_SelectedBNKfile = ttk.Button(frame_toparea, text = "Select BNK file...", width = 20,
                                                      command = lambda: self.handleButtonPress('__selected_bnk_file__'))                                             
        button_SelectedBNKfile.grid(row=1, column=0, padx=5, pady=5, sticky='e')
        
        # Text Entry Selected BNK file
        self.textfield_SelectedBNK = ttk.Entry(frame_toparea, width = 72)
        self.textfield_SelectedBNK.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        # Button Selected Seed file (sl1)
        button_Selectedsl1file = ttk.Button(frame_toparea, text = "Seed or SL1/MSL file...", width = 20, 
                                                      command = lambda: self.handleButtonPress('__selected_seed_file__'))                                             
        button_Selectedsl1file.grid(row=2, column=0, padx=5, pady=5, sticky='e')

        # Combo Box for Seeds, default to 0x00
        self.box_value = StringVar()
        self.combobox_SelectSeed = ttk.Combobox(frame_toparea, justify=LEFT, textvariable=self.box_value, width = 70)
        self.combobox_SelectSeed.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        self.combobox_SelectSeed.set('0000000000000000000000000000000000000000')

        # Checkbutton MSL file (casinos)
        self.mslcheck = IntVar()
        self.mslcheck.set(0)
        self.cb_mslcheck = Checkbutton(frame_toparea, text="MSL", justify=LEFT, variable = self.mslcheck, onvalue=1, offvalue=0)
        self.cb_mslcheck.grid(row=2, column=2, sticky='e',)
        
        # Text Label sl1 location
        self.label_SeedPath = ttk.Label(frame_toparea, text = 'Not Using SL1 file', width = 80)
        self.label_SeedPath.grid(row=3, columnspan=4, padx=5, pady=5, sticky = 'w')

        ######################### MIDDLE FRAME
        frame_middleframe = ttk.Frame(self.root)
        frame_middleframe.pack(side = TOP, fill=X)
        
        # Need to use .pack() for scrollbar and text widget
        frame_textarea = ttk.Labelframe(frame_middleframe, text="Output")
        frame_textarea.pack(side = LEFT)
        frame_textarea.config(relief = RIDGE, borderwidth = 0)

        # Text Area output of BNK file generation
        self.text_BNKoutput = Text(frame_textarea, width=80, height=25)
        S = Scrollbar(frame_textarea, command=self.text_BNKoutput.yview)
        S.pack(side=RIGHT, fill=Y)
        self.text_BNKoutput.configure(yscrollcommand=S.set)
        self.text_BNKoutput.pack(side=LEFT)
        
        #Frame for Checkbuttons
        frame_checkbuttons = ttk.Labelframe(frame_middleframe, text="Output Options")
        frame_checkbuttons.pack(side = RIGHT, fill=BOTH, expand = True)
        frame_checkbuttons.config(relief = RIDGE, borderwidth = 0)
        
        # Checkbutton Reverse
        self.reverse = IntVar()
        self.reverse.set(0)
        self.cb_reverse = Checkbutton(frame_checkbuttons, text="QCAS expected output", justify=LEFT, variable = self.reverse, onvalue=1, offvalue=0)
        self.cb_reverse.grid(row=1, column=1, sticky='w')

        # Checkbutton Uppercase
        self.uppercase = IntVar()
        self.uppercase.set(0)
        self.cb_uppercase = Checkbutton(frame_checkbuttons, text="Uppercase", justify=LEFT, variable = self.uppercase, onvalue=1, offvalue=0)
        self.cb_uppercase.grid(row=2, column=1, sticky='w')

        # Checkbutton 8 Char
        self.eightchar = IntVar()
        self.eightchar.set(0)
        self.cb_eightchar = Checkbutton(frame_checkbuttons, text="8 character spacing", justify=LEFT, variable = self.eightchar, onvalue=1, offvalue=0)
        self.cb_eightchar.grid(row=3, column=1, sticky='w',)

        ################ Bottom FRAME ##############
        frame_bottombuttons = ttk.Frame(self.root)
        frame_bottombuttons.pack(side=BOTTOM, fill=BOTH, expand = True)
        frame_bottombuttons.config(relief = RIDGE, borderwidth = 0)
        
        # Clear Button
        self.button_clear = ttk.Button(frame_bottombuttons, text = "Clear", command = lambda: self.handleButtonPress('__clear__'), width = 10)
        self.button_clear.grid(row=1, column = 1, padx=5, pady=5, sticky='e',) 

        # Start Button
        button_start = ttk.Button(frame_bottombuttons, text = "Start...",
                                  command = lambda: self.handleButtonPress('__start__'), width = 10)
        button_start.grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.root.mainloop()

    # Constructor
    def __init__(self):
        self.bnk_filename = ''
        self.bnk_filepath = ''
        self.seed_filepath = ''
        self.seed = ''
        self.root = Tk()
        self.setupGUI()

def main():
    app = epsig2()

if __name__ == "__main__": main()
