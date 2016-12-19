#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Script to read all bibcodes from the specified tex files (default *.tex), then
find the ADS bibtex entry and write it to the specified output (bibliography.bib).

"""
import re, glob, sys, argparse, os
import bibtexparser
from bibtexparser.bparser import BibTexParser


def parse_bibcodes_from_tex(inputfile):
    """
    Parses a tex file for all the bibcodes in it
    
    Argument:
    ---------
    
    inputfile : string
        (path to) file which to parse
        can be string with wildcards or list of strings as well
        
    Output:
    -------
    
    a list of all the bibcodes cited in the tex file
    """
    #
    # process input string or list
    #
    if type(inputfile) == str:
        inputfile = [inputfile]
    files = []
    for f in inputfile:
        files += glob.glob(f)
    #
    # cycle through all files and parse for bibcodes
    #
    # results = []
    # for f in files:
    #     with open(f) as o:
    #         text    = ''.join(o.readlines())
    #     matches = re.findall(r'\\cite[^{]*?[^}]*',text)
    #     for m in matches:
    #         results += re.sub('[^{]*{(.*)',r'\1',m).split(',')            
    results = []
    P = re.compile(r"\cite(?:p|alp|alt|t)?(\[.*?\])*{(.*?)}")
    def match_nested_cites(text):
        res = []
        for nested, cites in P.findall(text):
            res+=cites.split(',')
            res+=match_nested_cites(nested)
        return res

    for f in files:
        with open(f) as o:
            text    = [line.strip() for line in o.readlines()]
            text    = ''.join(text)
        results += [cite for cite in match_nested_cites(text)]
    #
    # we don't want double entries
    #            
    return list(set(results))
    
    
def ads_bibtex_from_bibcode(bibcodes):
    """
    Gets a dictionary of bibtex entries from NASA ADS,
    given a list of ADS bibcodes.
    
    Arguments:
    ----------
    
    bibcodes : array of string
        the bibcodes for which to retrieve the bibtex entries
        
    Returns:
    --------
    
    A dictionary with the bibcodes as keys and the  bibtex as entries
    """
    import urllib2
    #
    # construct query
    #
    bib_split = '\r\n'
    URL  = r'http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?db_key=ALL&warnings=YES&version=1&bibcode=%s&nr_to_return=1000&start_nr=1&data_type=BIBTEX&sort=NDATE'%(urllib2.quote(bib_split.join(bibcodes)))
    #
    # get the data
    #
    response = urllib2.urlopen(URL)
    html = response.read()
    response.close()
    #
    # split up in lines, remove header, remove empty lines
    #
    html = html.split('\n')
    
    while (len(html)>0) and (html[0]=='' or html[0][0]!='@'):
            del html[0]
    html=[l for l in html if l!='']
    html = '\n'.join(html)
    #
    # parse text
    #
    parser = BibTexParser()
    #parser.customization = homogeneize_latex_encoding
    db = bibtexparser.loads(html, parser=parser)        
    return db.get_entry_dict()
    
def bibtex_from_bibfile(bibfile):
    """
    Gets a dictionary of bibtex entries from a .bib file.
    
    Arguments:
    ----------
    
    bibfile: string
        the filename
        
    Returns:
    --------
    
    A dictionary with the bibcodes as keys and the  bibtex as entries
    """
    if not os.path.isfile(bibfile): raise ValueError('bib file not found')
    
    with open(bibfile) as f: text=f.readlines()
    
    while (len(text)>0) and (text[0]=='' or text[0][0]!='@'):
            del text[0]
    text=[l for l in text if l not in ['','\n'] ]
    text = ''.join(text)
    #
    # parse text
    #
    parser = BibTexParser()
    #parser.customization = homogeneize_latex_encoding
    db = bibtexparser.loads(text, parser=parser)        
    return db.get_entry_dict()
 
def clean_journals(entry_list):
    """
    Replace given journal names with the defualt latex macros.
    
    Arguments:
    ----------
    
    entry_list : list
        List of bibtex entries (each is a dict)
        
    Returns:
    --------
    
    entry_list : list
        The same list, but matching journal names replaced with AAS macros
    """
    macros = {
            '\\mnras':['Monthly Notices of the Royal Astronomical Society'],
            '\\icarus':['Icarus','Icarus (ISSN 0019-1035)'],
            '\\aap':['Astronomy and Astrophysics','Astronomy & Astrophysics'],
            '\\apj':['The Astrophysical Journal','Astrophysical Journal'],
            '\\nat':['NATURE-LONDON-','Nature'],
            '\\apjl':['The Astrophysical Journal Letters'],
              }
    output_list = []
    for entry in entry_list:
        if entry.has_key('journal'):
            journal = entry['journal']
            for abbrev,names in macros.iteritems():
                if journal in names:
                    entry['journal'] = abbrev
                    break
        output_list += [entry]
    return output_list
            

def clean_entries(entry_dict,keys=['doi']):
    """
    removes several entries that we don't want to save
    """
    pop_keys = ['uri','local-url','rating','date-modified','date-added']+keys
    for bibcode,entry in entry_dict.iteritems():
        for key in pop_keys:
            if key in entry.keys():
                entry_dict[bibcode].pop(key)
        if entry.has_key('doi'):
            entry['doi'] = entry['doi'].replace('_','\_')


if __name__=='__main__':
    #
    # parse input
    #
    RTHF = argparse.RawTextHelpFormatter
    PARSER = argparse.ArgumentParser(description=__doc__,formatter_class=RTHF)
    PARSER.add_argument('-b', '--bibtex-file',\
        help='Specify the output bibtex file name',type=str,
                        default='bibliography.bib')
    PARSER.add_argument('-m', '--mask',\
        help='Specify the mask matching the tex files',type=str,
                        default='*.tex')
    PARSER.add_argument('-o', '--overwrite',\
        help='Always overwrite existing file, do not ask user.',action='store_true')
    PARSER.add_argument('-c', '--copy',\
        help='Always copy all (also unused) existing entries to new file without asking.',action='store_true')

    ARGS     = PARSER.parse_args()
    yn       = ARGS.overwrite*'y'+''
    yn2      = ARGS.copy*'y'+''
    fname    = ARGS.bibtex_file 
    tex_mask = ARGS.mask
    
    bibliography = {}
    
    while os.path.isfile(fname) and yn not in ['y','n']:
        yn=raw_input('Do you want to overwite originals? [y/n] ').lower()

    if yn=='n':
        print('CANCELLED')
        sys.exit()

    # read in original bibcodes
        
    if os.path.isfile(fname):        
        print('Parsing bibcodes from original bib file')
        bibliography = bibtex_from_bibfile(fname)


    print('Parsing bibcodes from tex file')
    bibcodes    = parse_bibcodes_from_tex(glob.glob(tex_mask))
    bibcodes    = [b.strip() for b in bibcodes]
    entries_out = []

    # using existing bibcodes (remove them to keep track of used ones)
    
    if bibcodes!=[]:
        i = 0
        while i<len(bibcodes):
            bibcode = bibcodes[i]
            if bibcode in bibliography.keys():
                entries_out+=[bibliography[bibcode]]
                bibcodes.remove(bibcode)
                del bibliography[bibcode]
            else: i+=1

    # if there are unset bibentries, get them from ADS
            
    if bibcodes!=[]:
        print('Getting missing bibcodes from ADS')
        ads_library=ads_bibtex_from_bibcode(bibcodes)
        clean_entries(ads_library)
        i = 0
        while i<len(bibcodes):
            bibcode = bibcodes[i]
            if bibcode in ads_library.keys():
                entries_out+=[ads_library[bibcode]]
                bibcodes.remove(bibcode)
            else: i+=1

    if bibcodes!=[]:
        print('The following bibcodes were not found locally or in ADS:')
        for b in bibcodes: print('    {}'.format(b))
            
    if len(bibliography)>0:
        while yn2 not in ['y','n']:
            print('Entries found in original bib file, but not used in tex files')
            yn2=raw_input('Do you want to keep them in the bib file? [y/n] ').lower()
        if yn2=='y':
            print('Copying unused, existing entries:')
            for k,v in bibliography.iteritems():
                print('    {}'.format(k))
                entries_out+=[v]

    # clean journal names

    entries_out = clean_journals(entries_out)

    if entries_out!=[]:
        print('Writing out bibliographic entries to '+fname)
        
        f = open(fname,'w')
        db=bibtexparser.bparser.BibDatabase()
        db.entries += entries_out
        bib_string = bibtexparser.dumps(db)
        # some fixes
        bib_string = bib_string.replace(u'ρ',r'{$\rho$}')
        bib_string = bib_string.replace(u'μ',r'{$\mu$}')
        bib_string = bib_string.replace(u'σ',r'{$\sigma$}')
        f.write(bib_string.encode('utf-8'))
        f.close()
    else:
        print('No bibcodes found')