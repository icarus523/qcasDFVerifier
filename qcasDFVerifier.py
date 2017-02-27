import os
import csv
import sys
import epsig2
import hashlib
import hmac
import json
import random
import getpass
import difflib

from datetime import datetime
from threading import Thread

PATH_TO_BINIMAGE = 'G:\OLGR-TECHSERV\BINIMAGE'
#PATH_TO_BINIMAGE = 'binimage'

VALID_HASH_FILE_TYPES = ['BLNK', 'SHA1'] # only process these types of files
VALID_MID = ['00', '01','05','07','09','12','17'] 
VALID_MANUFACTURERS = ['ARI','IGT','ARU','KON','AGT','VGT']
QUIET_MODE = False

p_reset = "\x08"*8

### MODE CONTROL
VALIDATE_MSL_FILES = True
VALIDATE_PSL_FILE = True
GENERATE_NEW_GAMES_LIST = True
GENERATE_GAMES_LIST_TO_BE_REMOVED = False
DIFF_PSL_FILES = False
GENERATE_HASHES = False
VALIDATE_OLD_GAMES = False

# This script will automatically generate the hashes from the generated
# TSL file and compare it against the epsig generated PSL files.
#
# Some verifications of hashes will also occur to confirm that the
# Process has completed satisfactorily. 

class FileObject():

    def __init__(self, psl1, psl2, msl1, msl2, tsl, tsl_all, oldpsl1, oldpsl2):
        if os.path.isfile(psl1) and os.path.isfile(psl2) and os.path.isfile(msl1) and os.path.isfile(msl2) and os.path.isfile(tsl) and os.path.isfile(tsl_all) and os.path.isfile(oldpsl1) and os.path.isfile(oldpsl2):

            self.psl1 = psl1
            self.psl2 = psl2
            self.msl1 = msl1
            self.msl2 = msl2
            self.tsl = tsl
            self.tsl_all = tsl_all
            self.oldpsl1 = oldpsl1
            self.oldpsl2 = oldpsl2
            
        else:
            print("Check input parameters, not a file: ")
            sys.exit(1)

    def printFiles(self):
        print(self.psl1 + "\n" + self.psl2 + "\n" +  self.msl1+ "\n" +
              self.msl2+ "\n" +  self.tsl + "\n" +  self.tsl_all)

    def getMSLfiles(self):
        return [self.msl1, self.msl2]

    def getTSLfile(self):
        return self.tsl
    
    def getTSLfileAll(self):
        return self.tsl_all

    def getPSLfile(self):
        return [self.psl1 , self.psl2]

    def getOldPSLfile(self):
        return [self.oldpsl1, self.oldpsl2]

class qcasDatafilesVerifier():

    def __init__(self, args):

        self.ARI_PSL = list()
        self.IGT_PSL = list()
        self.PAC_PSL = list()
        self.VID_PSL = list()
        self.KON_PSL = list()
        self.AGT_PSL = list()
        self.VGT_PSL = list() # no longer active, but still in TSL file

        # Put files in an FileObject object for easier access.
        # Refer to Class definition for usage
        self.files_object = FileObject(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])

        # Main Method to implement Checks for CHK01 Datafile generation
        self.DoCheckList() # Start Check

    def GetMonth(self, datestr):
        #date = datestr.split("_")
        date = datetime.strptime(datestr, "qcas_%Y_%m_v%d.psl").date()
        return " " + date.strftime("%B %Y")

    def DiffPSLFiles(self, fname1, fname2):
        outputfile = "diff" +os.path.basename(fname1)+"_vs_" + os.path.basename(fname2) + ".txt"
        
        with open(fname1,'r') as oldpsl1:
            with open(fname2, 'r') as newpsl1:
                diff = difflib.unified_diff(
                    oldpsl1.readlines(),
                    newpsl1.readlines(),
                    fromfile=fname1,
                    tofile=fname2,)

                with open(outputfile, 'w+') as output: 
                    print("Writing DIFF file to disk: " + outputfile)
                    for line in diff:
                        #sys.stdout.write(line)
                        output.write(line)
                    print("Writing DIFF file to disk: " + outputfile)

    def DoCheckList(self):
        # Validate MSL files
        if VALIDATE_MSL_FILES:
            print("####################### VALIDATE MSL FILES")
            mslstatus = list() # list of bools
            mslfilelist = self.files_object.getMSLfiles() 
            for mslfile in mslfilelist: 
                mslstatus.append(self.ValidateMSLfile(mslfile))
                
            # Read Seed Files
            # self.Seeds[0] - first month
            # self.Seeds[1] - second month
            for item in mslstatus: 
                if item == True:
                    pass
                else: 
                    print("Halting! MSL files has issues")
            
            self.Seeds = self.ReadSeedList() 

        if GENERATE_NEW_GAMES_LIST: 
            # Generate New Games List
            print("######################## NEW GAME NAMES")
            newgamelist = self.ReadTSLfile(self.files_object.getTSLfile())
            print("New Games List are: ")
            print("%(game_name)-50s %(ssan)10s %(game_fname)30s  " %  \
                            { "game_name" : "-= GAME NAME =-" , "ssan" : "-= SSAN =-",  "game_fname": "-= FILE NAME =-" })
            for game in newgamelist:
                #print(json.dumps(game, sort_keys=True, indent=4, separators=(',',':')))
                #print(game['game_name'] + "\tSSAN: " + game['ssan'] + "\tFileName: " + game['game_fname'])
                print("%(game_name)-50s %(ssan)10s %(game_fname)30s  " %  \
                            { "game_name" : game['game_name'] , "ssan" : game['ssan'],  "game_fname": game['game_fname'] })

        if GENERATE_GAMES_LIST_TO_BE_REMOVED:
            # Game Names Removed
            print("######################## GAME NAMES REMOVED")
            # TO BE ADDED IDENTIFY GAME NAMES REMOVED FROM THE TSL FILE LIST

        if DIFF_PSL_FILES: 
            print("######################## DIFF OF CURRENT GOOD PSL FILE AND NEWLY GENERATED PSL FILE")
            # Need to identify PSL files of the same month (utilising same seed)
            # Otherwise comparison will be useless.

            for month in self.files_object.getOldPSLfile():
                for newmonth in self.files_object.getPSLfile():
                    if self.GetMonth(os.path.basename(newmonth)) == self.GetMonth(os.path.basename(month)):
                        print("Diffing: " + self.GetMonth(os.path.basename(newmonth)) + " and " + self.GetMonth(os.path.basename(month)))
                        self.DiffPSLFiles(month, newmonth)
                    else:
                        print("Can't Compare PSL months: " + self.GetMonth(os.path.basename(self.files_object.getOldPSLfile()[0])), self.GetMonth(os.path.basename(self.files_object.getPSLfile()[0])))

        if GENERATE_HASHES:       
            # New Games Only
            # For each item in the generated TSL file generate its corresponding Hash.
            NewGamesHashList = list()
            for month in self.Seeds:
                hashlist = Thread(target=self.GenerateHash_from_TSLfile(self.files_object.getTSLfile(), month)).start()
                NewGamesHashList.append(hashlist)
                
            # Pick a random seed in the seed list
            # Using this seed Display all new Games hash details.
            for i in range(len(self.Seeds)):
                # NewGamesHashList is a list [Month1, Month2] of generated_hashes game dict
                # self.Seeds is a list of seeds for [Month1, Month2]
                # so iterate both at the same time, using Month1 Hashlist with Month1 Seeds
                self.printDetailsUsingHash(NewGamesHashList[i], random.choice(self.Seeds[i]))

        
        # Read TSL file and generate a Game Object list
        AllGames_TSL = self.ReadTSLfile(self.files_object.getTSLfileAll())
        # game_tsl = { 'mid' : row['mid'],
             # 'ssan' : row['ssan'],
             # 'game_name' : row['game_name'].strip(),
             # 'game_fname' : row['binimage'].strip(),
             # 'bin_type' : row['bin_type']
            # } 

        if VALIDATE_PSL_FILE:                             
            # Read PSL file and generate Manufacturer PSL items
            # Validate each PSL file read
            pslfilelist = self.files_object.getPSLfile() 
            for pslfile in pslfilelist: 
                PSL_from_file = self.ReadPSLfile(pslfile)
                with open(pslfile, 'r') as file: 
                    
                    try:
                        pslentry = file.readline().split(",")  # Read only the first line of the PSL file and obtain Month and Year               
                        year = pslentry[2] 
                        month = pslentry[3]
                    except csv.Error as e:
                        sys.exit('file %s, line %d: %s' % (pslfile, file.line_num, e))
                
                    self.ValidatePSLfile(PSL_from_file, pslfile, year, month)

        if GENERATE_HASHES and VALIDATE_PSL_FILE:
            # Read PSL file (both) and verify the generated games (w/hashes) are in those two PSL files.
            for i in range(len(self.files_object.getPSLfile())):
                self.VerifyNewGeneratedGames_in_PSLfile(pslfilelist[i], NewGamesHashList[i])


        if VALIDATE_OLD_GAMES: 
            # Old Games Verification
            # Randomly choose one existing game for each manufacturer and generate hash of that game using the daily seed for that month. 
            # Compare these hashes to those in generated PSL file. 
            RandomARIGame = random.choice(self.ARI_PSL)
            # identify filename in TSL file (overall) given Random game's SSAN.
            
            for game in AllGames_TSL: 
                if game['ssan'] == RandomARIGame['ssan']:
                    filename_ARIGame = os.path.join(PATH_TO_BINIMAGE, self.getMID_Directory(game['mid']), game['game_fname'] + "." + self.getBINType(game['bin_type']))
                    
            RandomSeed = random.choice(self.Seeds[i]) # Get Random Seed
    
    def ValidateMSLfile(self, fname): 
        check_Year = False
        check_Month = False
        check_filename = False
        check_num_of_seeds = False
        
        
        MSL_Filename = os.path.basename(fname) # strip out path
        MSL_entry = self.ReadMSLfile(fname)
        
        print("Validating MSL file: " + MSL_Filename,  end=" > ")
        
        # Verify month and year against the filename itself. 
        # filename is in the format of: qcas_2016_03_v01.msl
        print("Year", end="...> ")
        mslfilenamelist = MSL_Filename.split("_") # Output is: ['qcas', '2016', '03', 'v01.msl']
        if not mslfilenamelist[1] == MSL_entry['year']:
            print("MSL Check FAILED: YEAR does not match in MSL file: " + mslfilenamelist[1], MSL_entry['year'])
        else: 
            print("OK", end="> ")
            check_Year = True
        
        print("Month", end="...> ")
        if not mslfilenamelist[2] == MSL_entry['month']:
            print("MSL Check FAILED: MONTH does not match in MSL file: " + mslfilenamelist[2], MSL_entry['month'])
        else: 
            print("OK", end="> ")
            check_Month = True
            
        # Verify contains seed data for each day
        # Count that the seed list has 31 entries. 
        print("Number of Seeds: ", end="...> ")
        if not len(MSL_entry['seeds']) == 30: # start at 0
            print("MSL Check FAILED: Invalid number of Seeds in MSL file: " + str(len(MSL_entry['seeds'])))
        else:
            print("OK", end="> \n")
            check_num_of_seeds = True
        
        if check_Year and check_Month and check_num_of_seeds: 
            return True
        else: 
            return False
            
    # Purpose Verify the content of each PSL including that they refer to the correct month, year and contains 
    # hash data for all manufactures. This can be done by ensuring all active Manufacturers have entries 
    # represented by their Machine ID, in the second column of the file. E.g AGT’s is ‘12’.
    def ValidatePSLfile(self, psl_dict_list, fname, year, month): 
        PSL_Filename = os.path.basename(fname) # strip out path

        print("\n\nValidating PSL file: " + PSL_Filename, end="")
        
        # Verify month and year against the filename itself. 
        # filename is in the format of: qcas_2016_03_v01.msl
        pslfilenamelist = PSL_Filename.split("_") # Output is: ['qcas', '2016', '03', 'v01.psl']
        if not pslfilenamelist[1] == year:
            print("MSL Check FAILED: YEAR does not match in MSL file: " + pslfilenamelist[1], MSL_entry['year'])
            sys.exit(2)
        else: 
            print("... PSL YEAR: OK", end="")
            
        if not pslfilenamelist[2] == month:
            print("MSL Check FAILED: MONTH does not match in MSL file: " + pslfilenamelist[2], MSL_entry['month'])
            sys.exit(2)
        else: 
            print("... PSL MONTH: OK", end="")        
            
        current_year = year # Generate current year from somwhere
        current_month = month # Generate current month
        
        for item in psl_dict_list: 
            if any(str(item['mid']).upper().strip() in s for s in VALID_MID): # Validate for active MIDs
                pass
            else: 
                print("\n\n" + PSL_Filename + ": PSL Check FAILED: Invalid MID: " + item['mid'])          
                sys.exit(2)
        
            # validate the year in each PSL entry are the same. 
            if item['year'] == current_year: 
                current_year = item['year'] # check the next game
            else: 
                print("\n\n" + PSL_Filename + ": PSL Check FAILED: Different YEAR found in PSL entry: " + item['year'] + "\tSSAN: " + item['ssan'])          
                sys.exit(2)
            
            # validate the month in each PSL entry are the same. 
            if item['month'] == current_month: 
                current_month = item['month'] # check the next game
            else: 
                print("\n\n" + PSL_Filename + ": PSL Check FAILED: Different MONTH found in PSL entry: " + item['month'] + "\tSSAN: " + item['ssan'])          
                sys.exit(2)
        
        # Verify that valid MIDs have PSL entries. 
        combined_PSL = [self.ARI_PSL, self.IGT_PSL, self.PAC_PSL, self.VID_PSL, self.KON_PSL, self.AGT_PSL, self.VGT_PSL] 
        print("\n\nValidating valid MIDs have PSL entries: ")
        for i in range(len(VALID_MANUFACTURERS)): 
            if len(combined_PSL[i]) < 1 :
                print("\n\n" + PSL_Filename + ": PSL Check FAILED: " + str(VALID_MANUFACTURERS[i]) + " PSL entries is only: " +  len(combined_PSL[i]) + " in size")
                sys.exit(2)
            else: 
                print(str(VALID_MANUFACTURERS[i] + " PSL Contents...OK"), end=" ") 
            
    def ReadMSLfile(self, fname): 
        seedlist = list()
        with open(fname, 'r') as psl:
            pslentry = csv.reader(psl, delimiter=',')
            try:
                included_cols = [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]
                for row in pslentry:
                    seedlist = list(row[i] for i in included_cols)
                    year = row[0] 
                    month = row[1]
                
                MSL = { 'year' : year, 'month': month, 'seeds': seedlist}
            except csv.Error as e:
                sys.exit('file %s, line %d: %s' % (fname, sl1file.line_num, e))
        return MSL
        
    # input: filename for PSL file
    # output: a list of dicts: [{ manufacturer : MID_psl_info }, { manufacturer : MID_psl_info },]
    def ReadPSLfile(self, fname): 
        PSL_entry_list = list()
        
        with open(fname, 'r') as psl:
            pslentry = csv.reader(psl, delimiter=',')
            try:
                included_cols = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35]
                for row in pslentry:
                    hashlist = list(row[i] for i in included_cols)
                    mid = row[1] # mid
                    year = row[2] 
                    month = row[3]
                    ssan = row[4] # extract ssan
                    game_name = row[0] # game name
                    
                    # create dict object for psl row entry
                    psl_info = {'game_name' : game_name, 'mid': mid, 'ssan': ssan, 'hashlist': hashlist, 'year': year, 'month' : month}
                    
                    if mid == '00': # ARI
                        self.ARI_PSL.append(psl_info)
                    elif mid == '01': # IGT
                        self.IGT_PSL.append(psl_info)
                    elif mid == '05': # PAC
                        self.PAC_PSL.append(psl_info)
                    elif mid == '07': # VID
                        self.VID_PSL.append(psl_info)
                    elif mid == '09': # KONAMI
                        self.KON_PSL.append(psl_info)
                    elif mid == '12': # AGT
                        self.AGT_PSL.append(psl_info)
                    elif mid == '17': # VGT
                        self.VGT_PSL.append(psl_info) # no longer active, but still in TSL file
                    else: 
                        # Put a check here to verify "active" MIDs are only being used. 
                        print("Unknown MID: " + str(row))
                    
                    PSL_entry_list.append(psl_info)
    
            except csv.Error as e:
                sys.exit('file %s, line %d: %s' % (fname, psl.line_num, e))
    
        return PSL_entry_list
    
    # input: PSLfilelist [pslfile1, pslfile2], and NewGamesHashList (contains all Hashes generated from TSL file)
    # in the following structure: 
    #                        generated_hashes = {'seed': seeds,
    #                                        'hash': oh,
    #                                        'game_name' : game['game_name'],
    #                                        'ssan' : game['ssan']
    #                                        }
    # output: True/False (boolean) if NewGamesHashList is present in PSLfile_list
    def VerifyNewGeneratedGames_in_PSLfile(self, PSLfile, NewGamesHashList):
        
        # 1. Read PSLfile (CSV format)
        # 2. Identify added games (strip it out of the file), use SSAN.
        # 3. For each Game in the NewGamesHashList, compare this with the hash result in the PSL file
        print("\n\nVerifying new games Generated Hashes against Expected Hashes in the PSL file: " + os.path.basename(PSLfile))
        if not QUIET_MODE:
            print("%(game_name)-30s %(mid)3s %(year)04s %(month)5s %(ssan)10s %(dom)03s %(seed)8s %(generated_hash)15s  %(expected_hash)15s " %  \
                        { "game_name" : "Game Name" , "mid": "MID", "year": "Year", "month": "Month", "ssan" : "SSAN", "dom": "Day", "seed": "Seed", "generated_hash": "Generated Hash", "expected_hash" : "Expected Hash in PSL"})
        else: 
            print("\nDay: ", end="")
        with open(PSLfile, 'r') as psl:
            pslentry = csv.reader(psl, delimiter=',')
            try:
                included_cols = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35]
                for row in pslentry:
                    hashlist = list(row[i] for i in included_cols)
                    mid = row[1] # mid
                    year = row[2] 
                    month = row[3]
                    ssan = row[4] # extract ssan
                    game_name = row[0] # game name
                    
                 
                    for game in NewGamesHashList:
                        
                        # format the Game Hash to QCOM PSL format. 
                        mod_game_hash = self.getQCAS_Expected_output(game['hash'].lstrip('0x').upper())
                        
                        # Search for hashes that's been generated in the new Games Hash List (from TSL) and 
                        # compare that with the PSLfile being processed. 
                        # Output details of the PSL file if matches 
                        if any(mod_game_hash in s for s in hashlist):
                            # matches ! 
                            pslentry_index = hashlist.index(mod_game_hash)
                            if not QUIET_MODE:
                                print("%(game_name)-30s %(mid)3s %(year)04s %(month)5s %(ssan)10d %(dom)3d %(seed)8s %(generated_hash)15s  %(expected_hash)15s " %  \
                                { "game_name" : game_name , "mid": str(mid), "year": year, "month": month, "ssan" : int(ssan), "dom": pslentry_index, "seed": str(game['seed']), "generated_hash": mod_game_hash, "expected_hash" : str(hashlist[pslentry_index])})
                            else: 
                                if mod_game_hash == str(hashlist[pslentry_index]): # generated hash == expected hash
                            #    print("%(dom)2d[Hash:%(hash)8s]" % { 'dom' : pslentry_index, 'hash': str(hashlist[pslentry_index] )}, end=" ") 
                                
                                    print("%(seed)8s %(generated_hash)15s %(expected_hash)15s " %  { "seed": str(game['seed']), "generated_hash": mod_game_hash, "expected_hash" : str(hashlist[pslentry_index])}, end=" ")
            except csv.Error as e:
                sys.exit('file %s, line %d: %s' % (fname, psl.line_num, e))
        


    # input: filename TSL file
    # output: Games List of Game Objects 
    def ReadTSLfile(self, fname):
        input_fieldnames = ['mid', 'ssan','game_name','binimage','bin_type']
        GameList = list()

        if not os.path.isfile(fname):
            print("Error, file cannot be found" + fname)
            sys.exit(1)
        
        input_fieldnames = ['mid', 'ssan','game_name','binimage','bin_type']
        
        try:
            with open(fname, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', fieldnames=input_fieldnames)
                for row in reader:
                    if any(str(row['bin_type']).upper().strip() in s for s in VALID_HASH_FILE_TYPES): # validate file type
                        game = { 'mid' : row['mid'],
                                     'ssan' : row['ssan'],
                                     'game_name' : row['game_name'].strip(),
                                     'game_fname' : row['binimage'].strip(),
                                     'bin_type' : row['bin_type']
                                    } 
                        GameList.append(game)
                    #else:
                    #    print("Not generating hash for: " + str(row['game_name']), str(row['bin_type']).strip())
                        
        except csv.Error as e:
            sys.exit('file %s, line %d: %s' % (fname, reader.line_num, e))
        
        return GameList
            
    def getQCAS_Expected_output(self, text):
        tmpstr = text[:8] # Returns from the beginning to position 8 of uppercase text
        return "".join(reversed([tmpstr[i:i+2] for i in range(0, len(tmpstr), 2)]))   
                    
    def GenerateHash_from_TSLfile(self, fname, seedlist):
        # Identify the file to hash
        # require: path to binimage, mid, and filename
        print("Generating Hashes for games in " + os.path.basename(fname))
        myCacheHash = list()
        oh = "0000000000000000000000000000000000000000"

        if not os.path.isfile(fname):
            print("Error, file cannot be found" + fname)
            sys.exit(1)
    
        newgamelist = self.ReadTSLfile(fname)
            
        # newgamelist, should now contains all new games from the TSL entry.
        # this can now be used to generate hashes for all seeds in the month

        NewGamesHashlist = list()
        generated_hashes = None
        # Generate Hashes for all new games in the new TSL game file
        # for seeds in the current month. 
        for seeds in seedlist:
            for game in newgamelist:
                if game['bin_type'] == 'BLNK': 
                    file_to_be_processed = os.path.join(PATH_TO_BINIMAGE, self.getMID_Directory(game['mid']), game['game_fname'] + "." + self.getBINType(game['bin_type']))
                
                    if not QUIET_MODE: 
                        print("\n\nProcessing: " + os.path.basename(file_to_be_processed))
                        print("Seed: " + seeds)
                        
                    with open(file_to_be_processed, 'r') as blnkfile: 
                        field_names = ['fname', 'type', 'blah']
                        reader = csv.DictReader(blnkfile, delimiter=' ', fieldnames = field_names)

                        for row in reader:
                            cached = False
                            if row['type'].upper() == 'SHA1': # only process HMAC SHA1 hashes (for seed use) inside BNK files. 
                                localhash = "00"
                                completefile = os.path.join(PATH_TO_BINIMAGE, self.getMID_Directory(game['mid']), str(row['fname']))
                                
                                # Implement caching list
                                # Look in the Cache for matching fname & seed "key", if it doesn't
                                # exist, generate the Hash for fname + seed combination & append it to the list, 
                                # else retrieve already generated hash from the list. 
                                # 
                                if not any(cached_item.get('fname', None) == completefile and cached_item.get('seed', None) == seeds for cached_item in myCacheHash):
                                    # does not exist
                                    localhash = self.dohash_hmacsha1(completefile, self.getQCAS_Expected_output(seeds), 65534) # Important! Reverse seed since QCAS datafiles 
                                    myCacheHash.append({ 'fname' : completefile, 'hash' : localhash, 'seed' : seeds})
                                else:
                                    cached = True
                                    for cached_item in myCacheHash:
                                        if completefile == cached_item['fname']:
                                            localhash = cached_item['hash'] # use cached hash

                                oh = hex(int(oh,16) ^ int(str(localhash), 16)) # XOR
                                if QUIET_MODE: 
                                    pass
                                else:
                                    if cached:
                                        print(str(localhash) + "\t" + str(row['fname']) + " (cached)")
                                    else: 
                                        print(str(localhash) + "\t" + str(row['fname']))

                            

                            else:
                                print("Not processing any other file other than SHA1!")
                                sys.exit(1)

                      
                        
                    generated_hashes = {'seed': seeds,
                                            'hash': oh,
                                            'game_name' : game['game_name'],
                                            'ssan' : game['ssan']
                                            }
                
                elif game['bin_type'] == 'SHA1': # support SHA1 i.e. .bin files
                    file_to_be_processed = os.path.join(PATH_TO_BINIMAGE, self.getMID_Directory(game['mid']), game['game_fname'] + "." + self.getBINType(game['bin_type']))

                    if not QUIET_MODE: 
                        print("\n\nProcessing: " + os.path.basename(file_to_be_processed))
                        print("Seed: " + seeds)
                    
                    if not any(cached_item.get('fname', None) == file_to_be_processed and cached_item.get('seed', None) == seeds for cached_item in myCacheHash):
                        localhash = self.dohash_hmacsha1(file_to_be_processed, self.getQCAS_Expected_output(seeds), 65534) # Important! Reverse seed since QCAS datafiles 
                    else:
                        for cached_item in myCacheHash:
                            if completefile == cached_item['fname']:
                                localhash = cached_item['hash'] # use cached hash
                        
                    oh = hex(int(oh,16) ^ int(str(localhash), 16)) # XOR *atleast with "00"    
                        
                    generated_hashes = {'seed': seeds,
                                            'hash': oh,
                                            'game_name' : game['game_name'],
                                            'ssan' : game['ssan']
                                            }

                if QUIET_MODE:
                    print("Processing %(file)30s Seed: %(myseed)8s Hash: %(hash)8s " % { 'file' : os.path.basename(file_to_be_processed), 
                    'myseed' : seeds, 
                    'hash': self.getQCAS_Expected_output(oh.lstrip('0x').upper())}, end="\n")
                        #print("%(dom)2d[Hash:%(hash)8s]..OK" % { 'dom' : pslentry_index, 'hash': str(hashlist[pslentry_index] )}, end=" ") 
                else: 
                    print("XOR Hash: " + oh)        
                                        
                NewGamesHashlist.append(generated_hashes)
                
        # NewGamesHashlist now includes all new games, for each seed, and hash.
        # In the following dict: { 'seed': seed of the day, 'hash': hash using seed of the day, 'game_name' : game name }
        return(NewGamesHashlist)

    # input: gamedictlist, seed 
    #       - gamedictlist contains all new games for the month in a dict list
    #       - seed is a randomly selected seed from a MSL (seedfile)
    # output: display on screen game details that matches the seed to verify that Hashes have been generated using
    #       the MSL files. 
    def printDetailsUsingHash(self, gamedictlist, seed):
        print("\nHashes for new games in the new TSL file with randomly selected seed of: " + str(seed))
        for game in gamedictlist:
            if game['seed'] == seed:
                # format game hash to QCAS format
                mod_game_hash = self.getQCAS_Expected_output(game['hash'].lstrip('0x').upper())
                print("SSAN: {0}\t{1}\t{2}".format(int(game['ssan']), game['game_name'], mod_game_hash.upper()))

    # input: file to be hashed using hmac-sha1
    # output: hexdigest of input file    
    def dohash_hmacsha1(self, fname, seed='00', chunksize=8192):
        key = bytes.fromhex(seed)
        m = hmac.new(key, digestmod = hashlib.sha1) # change this if you want other hashing types for HMAC, e.g. hashlib.md5
        done = 0
        size = os.path.getsize(fname)
        # Read in chunksize blocks at a time
        with open(fname, 'rb') as f:
            while True:
                block = f.read(chunksize)
                done += chunksize
                sys.stdout.write("%7d"%(done*100/size) + "%" + p_reset)
                if not block: break
                m.update(block)      
        return m.hexdigest()

    def getBINType(self, bin_type):
        if bin_type == 'BLNK':
            return "BNK"
        elif bin_type == 'SHA1': 
            return "BIN"
        else:
            print("Unknonw bin_type: " + bin_type)

    def getMID_Directory(self, mid):
    # Check if inactive manufacturers exist in TSL file
        if (mid == '00'): manufacturer = 'ARI'
        elif (mid == '01'): manufacturer = 'IGT'
        elif (mid == '05'): manufacturer = 'PAC'
        elif (mid == '07'): manufacturer = 'VID'
        elif (mid == '09'): manufacturer = 'KONAMI'
        elif (mid == '12'): manufacturer = 'AGT'
        elif (mid == '17'): manufacturer = 'VGT'
        else:
            print("Unknown mid: " + mid)
            sys.exit(1)
        return manufacturer
            
    def ReadSeedList(self):
        monthseedlist = list()

        for mslfile in self.files_object.getMSLfiles():
            monthseedlist.append(epsig2.epsig2.processsl1file(self, mslfile))

        return monthseedlist # [ month1, month 2]

def main():

    # arg[1] = PSL 1
    # arg[2] = PSL 2
    # arg[3] = MSL 1
    # arg[4] = MSL 2
    # arg[5] = TSL file containing only new games.
    # arg[6] = TSL file for all games

    # read the TSL file and for each file generate the hash.
    # compare this value 

    if (len(sys.argv) < 6):
        print('Not enough args. Try again')
        sys.exit(2)
    else:
        print("CHK01 Generated on: " + str(datetime.now()) + " by: " + getpass.getuser())
        app = qcasDatafilesVerifier(sys.argv[1:]) # Remove first element in sys.args

if __name__ == "__main__": main()
