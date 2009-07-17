#!/usr/local/bin/python2.5

######################################################################
# This script interacts with the MySQL DB storing the string-mrs pairs
# to identify those pairs which are universally ungrammatical, and
# mark them as such. It actually groups together a bunch of different
# filters, each of which corresponds to a field in the DB.
#
# If each filter corresponds to a field, then there should be three
# possible values for each filter on each string-mrs pair:
#
#      2 -- filter is not applicable
#      1 -- filter is applicable and this string-mrs pair passes
#      0 -- filter is applicable and this string-mrs pair does not pass
#
# Filters are `applicable' to all strings for the mrs_ids they care
# about.  With the above system, assuming `1' and `2' both map to `true'
# and `0' to `false', universally ungrammatical strings are those for
# which the AND of the universal filters is false.  Potentially grammatical
# ones are those for which the AND is true.
#
# This file defines the general types of filters and the function which
# calls and applies them.  Other files will import this one, define
# particular filters, and invoke them.

######################################################################
# TODO
#
# 1. Rework things so that this can be invoke with particular mrs_ids,
# and only pull items with those mrs_ids out of the DB for consideration.
# This will be useful when we are adding to an existing DB. ... Or not:
# presumably, adding i_ids means adding new filters, which means that
# we need values for each of those filters for the rest of the strings.
#
# 2. Come up with a more transparent naming scheme for the filter classes.

######################################################################
# ALTERNATIVE PSEUDOCODE -- probably more efficient and compact
#
# select i-id from MatrixTDB
#
# For each i-id in ids
#    for each filter
#        add [filter_name, filter_value] to dictionary
#    update DB entry for i-id with appropriate filter_value for each
#                     filter_name

######################################################################
# Preliminaries

import MySQLdb
import re
import sys

#######################################################################
# filter_string(mrs_id,string)
#
# Calls each individual filter on string-mrs pair.  Returns an array
# where the keys are the names of the filter fields and the values are
# the values assigned by each filter to the string-mrs pair.  Each
# particular filter should return its name and its value.

def filter_one_result(mrs_id, sent,filter_list,filter_id_hash):

    filter_values = {}

    for f in filter_list:
        filter_values[filter_id_hash[f.name]] = f.exe(mrs_id, sent)
        if filter_values[filter_id_hash[f.name]] == 0:
            break

    return filter_values

########################################################################
# Filter class

class Filter:
    def __init__(self,name,mrs_id_list,comment,fv = None):
        self.name = name
        self.mrs_id_list = mrs_id_list
        # TODO: don't use predefined 'type' function...is it supposed to be comment anyway?
        self.type = type
        self.fv = fv

    def check_mrs_id(self,mrs_id):
        return mrs_id in self.mrs_id_list

    # TODO: this function is wrong b/c it doesn't consider the fv lists in s_filters.py that end in a
    # colon.  E.g., fv = 'aux-verb:' which i think means if aux-verb is off given the context.  Of
    # course it looks like what's actually in the choices file is has-aux:, not aux-verb:
    def check_fv(self, fvset, fvlist = None):
        # TODO: there has to be a cleaner way to do this.
        # TODO: abstract this fv thing into a class instead of this list structure.
        if fvlist is None:
            if self.fv is None:
                # if it has None for self.fv, then it's probs a u filter
                # and it cares regardless of the lt's fvs
                # TODO: clean this up: two points of return
                return True
            else:
                fvlist = self.fv
                
        if fvlist[0] == 'and':
            for item in fvlist[1:]:
                answer = self.check_fv(fvset, item)
                # as soon as I get a False, get out of here
                if not answer:
                    break
        elif fvlist[0] == 'or':
            for item in fvlist[1:]:
                answer = self.check_fv(fvset, item)
                # as soon as I get a True, get out of here
                if answer:
                    break
        else:
            # TODO: there has to be a cleaner way to do this.
            # now what?
            # i should always be a string here, not a list of strings        
            if type(fvlist) is list:
                # or if i'm a list i should be a list of just one string
                if len(fvlist) > 1:
                    print >> sys.stderr, self.name
                    print >> sys.stderr, self.fv
                    print >> sys.stderr, len(fvlist)
                    for fv in fvlist:
                        print >> sys.stderr, fv
                    raise TypeError, "Ill-formed fv"
                else:
                    fvlist = fvlist[0]
            if fvlist in fvset:
                answer = True
            else:
                answer = False

        return answer

    def exe(self,mrs_id,sent, fvSet):
        if self.check_mrs_id(mrs_id) and self.check_fv(fvSet):
            answer = self.apply_filter(sent)
        else:
            answer = 2

        return answer

    #Might not need this here.
    def apply_filter(self,sent):
        print "Error"
        assert False


class FalseFilter(Filter):
    def apply_filter(self,sent):
        return 0


class MatchFilter(Filter):
    # Checking for something that must present
    def __init__(self,name,mrs_id_list,re1,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1

    def apply_filter(self,sent):
        if re.search(self.re1,sent):
            return 1
        else:
            return 0


class NotMatchFilter(Filter):
    # Checking for something that can't be present.
    def __init__(self,name,mrs_id_list,re1,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1

    def apply_filter(self,sent):
        if re.search(self.re1,sent):
            return 0
        else:
            return 1


class IfFilter(Filter):
    # Checking for something that must be present, but only under
    # some particular condition.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent):
            if re.search(self.re2,sent):
                return 1
            else:
                return 0
        else:
            return 1

class IfNotFilter(Filter):
    # Checking for something that must not be present, but only under
    # some particular condition.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent):
            if re.search(self.re2,sent):
                return 0
            else:
                return 1
        else:
            return 1


class OrFilter(Filter):
    # Checking for two things, one of which must be present.  This is
    # logically equivalent to checking for something that must be present,
    # but only if something else isn't present (if not A then B), and
    # used to be called NegTrigMatchFilter.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent) or re.search(self.re2,sent):
            return 1
        else:
            return 0


class AndFilter(Filter):
    # Checking for two things that must both be present.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent) and re.search(self.re2,sent):
            return 1
        else:
            return 0


class AndNotFilter(Filter):
    # Checking for one things that must be present and another
    # thing that must NOT be present.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent) and not re.search(self.re2,sent):
            return 1
        else:
            return 0


class NandFilter(Filter):
    # Checking for two things that can't both be present.  This is
    # the logical NAND (NOT AND) condition.
    def __init__(self,name,mrs_id_list,re1,re2,comment,fv = None):
        Filter.__init__(self,name,mrs_id_list,comment,fv)
        self.re1 = re1
        self.re2 = re2

    def apply_filter(self,sent):
        if re.search(self.re1,sent) and re.search(self.re2,sent):
            return 0
        else:
            return 1


######################################################################
# This function will be called in other files which define filters
# and then invoke it.
# 6/19/07 This seems to be used only for the universal filters.

def filter_results(filter_list,filter_type):

    #Connect to MySQL server
    db = MySQLdb.connect(host="localhost", user="ebender",
                         passwd="tr33house", db="MatrixTDB")

    #Create a cursor

    cursor = db.cursor()

    #Check whether all of the filters already correspond to fields
    #in the DB, and if not, create those fields.

    # FIX ME: There's code in run_specific_filters.py that does
    # something similar.

    for f in filter_list:

        name = f.name
        mrs_id_list = f.mrs_id_list
        cursor.execute("SELECT * FROM filter WHERE filter_name = %s", (name))
        record = cursor.fetchall()
        if record == ():
            cursor.execute("INSERT INTO filter SET filter_name = %s, filter_type = %s", (name,filter_type))
    

    #Get list of ids from DB.  
    #6/19/07 We have 21 million records in result now, so we can't load them all at once.
    
    #6/20/07 Last night the process stopped at item 6,900,001.  Restarting

    #6/20/07 We seem to be missing entries for 6,900,002, and possibly a couple
    #of others.

    cursor.execute("SELECT r_result_id FROM result LIMIT 8052044, 100000")
    ids = cursor.fetchall()
    limit =  9608642

    while ids != ():

        print "Now working results " + str(limit) + " through " + str(limit + 1000000)

        #`ids' is now a tuple containing elements for each item in a 100,000 slice of the
        #relevant table.  Each of those elements is a tuple which contains
        #just the r_result_id.

        #Based on the r_result_id, we are now going to get the string
        #and mrs_id.

        for id in ids:
            key = id[0]
            cursor.execute("SELECT r_mrs, i_input FROM result,parse,item WHERE result.r_result_id = %s AND result.r_parse_id = parse.p_parse_id AND parse.p_i_id = item.i_id", (key))
            (mrs_id, string) = cursor.fetchone()

            filter_values = filter_one_result(mrs_id,string,filter_list)

            #Should do error checking here: Are all of the values legit?

            for filter_key in filter_values.keys():
                cursor.execute("SELECT filter_id FROM filter WHERE filter_name = %s",
                               (filter_key))
                f_id = cursor.fetchall()
                if len(f_id) > 1:
                    print "Error: Multiple filters with the same name." + filter_key
                else:
                    value = filter_values[filter_key]
                    if not value == 2:
                        f_id = f_id[0][0]
                        cursor.execute("INSERT INTO res_fltr SET rf_res_id = %s, rf_fltr_id = %s, rf_value = %s",
                                       (key, f_id, filter_values[filter_key]))

        cursor.execute("SELECT r_result_id FROM result LIMIT %s, 100000", (limit))
        ids = cursor.fetchall()
        limit += 100000

def getFilterID(fname, conn):
    """
    Function: getFilterID
    Input:
        fname - the name of a filter
        conn - a MatrixTDBConn
        TODO: Do I need to add 'type' here to distinguish two that may have same name?
    Output: answer - the ID of this filter in MatrixTDB
    Functionality: looks in MatrixTDB for a filter of this name.
    """
    row = conn.selQuery("SELECT filter_id FROM filter " + \
                                            "WHERE filter_name = %s", (fname))
    try:
        answer = row[0][0]
    except IndexError:
        answer = 0
        
    return answer
    
def insertFilter(fname, ftype, conn):
    """
    Function: addFilter
    Input:
        fname - the name of a filter
        ftype - the type of filter, either u (universal) or s (specific)
        conn - a MatrixTDBConn
    Output: newID - the ID of this filter added to MatrixTDB
    Functionality: adds this filter to the filter table of MatrixTDB.
    """
    conn.execute("INSERT INTO filter SET filter_name = %s, filter_type = %s", (fname, ftype))
    fID = conn.selQuery("SELECT LAST_INSERT_ID()")[0][0]
    return fID

def insertFilteredSpecResult(resID, fltrID, appliedResult, conn):
    """
    Function: insertFilteredSpecResult
    Input:
    Output:
    Functionality:
    Author: KEN (Scott Halgrim, captnpi@u.washington.edu)
    Date: 7/9/09    
    TODO: comment this
    """
    
    conn.execute("INSERT INTO res_sfltr "+ \
                             "(rsf_res_id, rsf_sfltr_id, rsf_value) " + \
                         "VALUES (%s, %s, %s)", (resID, fltrID, appliedResult))
    return

def insertFilteredResult(resID, fltrID, appliedResult, conn):
    """
    Function: insertFilteredResult
    Input:
    Output:
    Functionality:
    Author: KEN (Scott Halgrim, captnpi@u.washington.edu)
    Date: 7/8/09    
    TODO: comment this
    """
    
    conn.execute("INSERT INTO res_fltr "+ \
                             "(rf_res_id, rf_fltr_id, rf_value) " + \
                         "VALUES (%s, %s, %s)", (resID, fltrID, appliedResult))
    return
