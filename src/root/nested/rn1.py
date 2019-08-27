#!/usr/bin/python3
import math, re, string
import requests
import pandas as pd
from bs4 import BeautifulSoup, NavigableString
import lxml.etree as ET
import pprint
import warnings
warnings.filterwarnings("ignore")

username = "hillenr"
password = "May2@150"
payload = {
	"username": username, 
	"password": password, 
}


def esc2char(input_str):
    translate = {
       '&sol;': '/',   
       '&bsol;': '\\',   
       '&lsqb;': '[',  
       '&rsqb;': ']',  
       '&num;': '#',   
       '&rdquor;': '"',
       '&verbar;': '|',
       '&lowbar;': '_',
       '&plus;': '+',  
       '&ast;': '*',   
       '&equals;': '=',
       '&percnt;': '%',
       '&dash;': '-',
    }
    for seq, char in translate.items():
        input_str = input_str.replace(seq, char)
    return(input_str)

def get_rn_items(section):
    dts2rn = {}
    for item in section.find_all("item"):
        rn = ""
        if isinstance(item, NavigableString):
            #print("item: ", item)
            continue
        #print(item.contents)
        dts = []
        for par in item.find_all("p"):
            if isinstance(par, NavigableString) or len(par.contents) == 0:
                #print("par: " , par)
                continue
            #print(par.contents)
            par_str = ""
            for tag in par.children:
                if isinstance(tag, NavigableString):
                    par_str = par_str + tag.string
                    continue
                tag_str = ""
                for subtag in tag.children:
                    if subtag.string is not None:
                        tag_str = tag_str + subtag.string
                if tag_str == "": continue
                if tag.name == "fmtbold":
                    par_str = par_str + "<b>" + tag_str + "</b>" 
                elif tag.name == "fmtemphasis":
                    par_str = par_str + "<i>" + tag_str + "</i>" 
                elif tag.name == "fmtnone":
                    par_str = par_str + tag_str 
            par_str = esc2char(par_str)
            m = re.search(r'\[\d{6}[ \d,]*(-MI|-MA)\]', par_str)
            if m:
                dts = re.findall('(\d{6})', m.group(0))
            #print(par_str)
            if rn == "":
                rn = par_str
            else:
                rn = rn + "\n" + par_str
        for d in dts:
            dts2rn[d] = rn
        #print("------------", dts, "-------------")    
    return(dts2rn)

def get_resolved(file_n):
    dts_s = {}
    with open(file_n) as fp:
       soup = BeautifulSoup(fp, features="lxml") 
    for l1 in soup.find_all("s"):
        if isinstance(l1, NavigableString):
            #print("l1: " , l1)
            continue
        release = re.search(r'Release (\d{2}\.\d{1,2}\.R\d{1,2}(-\d)?)', l1.title.string)[1]
        for l2 in l1.children:
            if isinstance(l2, NavigableString): continue
            title = l2.title
            if title is None: continue
            component = esc2char(title.string)
            dts2rn = get_rn_items(l2)
            dts_dict = {}
            for dts in dts2rn:
                dts_dict['rel'] = release
                dts_dict['comp'] = component
                dts_dict['wu'] = dts2rn[dts]
                dts_s[dts] = dts_dict.copy()
    return(dts_s)

def get_known(file_n):
    dts_s = {}
    with open(file_n) as fp:
       soup = BeautifulSoup(fp, features="lxml") 
    for l2 in soup.find_all("s"):
        if isinstance(l2, NavigableString): continue
        title = l2.title
        if title is None: continue
        component = esc2char(title.string)
        dts2rn = get_rn_items(l2)
        dts_dict = {}
        for dts in dts2rn:
            dts_dict['comp'] = component
            dts_dict['wu'] = dts2rn[dts]
            dts_s[dts] = dts_dict.copy()
    return(dts_s)

def combine_rel(major, minor):
    major = re.search(r'(\d+\.\d+).*', major)[1]
    m = re.search(r'^[0-9\.]*(([ISRBFisrb])?\d+(-\d+)?)$', minor)
    if m is None:
        return(major)
    if m.group(2) == "":
        minor = ".R" + m.group(1)
    else:
        minor = "." + m.group(1)
    return(major + minor)

def parse_dts(urls):
    dqs = {}
    login_url = "https://sso.mv.usa.alcatel.com/login.cgi"
    s = requests.session()
    r1 = s.post(
            login_url, 
            data = payload, 
            verify = False,
            headers = dict(referer=login_url)
    )
    #print(r1.text)
    for query in urls.keys():
        dts_s = {}
        r = s.get(
                url[query], 
                headers = dict(referer = url[query]),
                verify = False,
                cookies=r1.cookies
        )
        page = BeautifulSoup(r.text, features="lxml")
        table = page.find('table', id="subreport_list")
        #print(list(table.children))
        rows = table.find_all("tr")
        dts = ""
        for row in rows:
            dts_struct = {}
            rn = row.find('fieldset')
            if rn is None:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]
                if len(cols) == 0: continue
                print(cols)
                dts = re.search(r'(\d+)-', cols[1])[1]
                dts_struct['type'] = cols[0]
                dts_struct['sev'] = cols[3]
                dts_struct['state'] = cols[4]
                dts_struct['orig'] = cols[5]
                dts_struct['rn_flag'] = cols[9]
                dts_struct['4ls'] = cols[10]
                dts_struct['title'] = cols[11]
                dts_struct['found_in'] = combine_rel(cols[13], cols[14])
                dts_struct['rn'] = None
                dts_s[dts] = dts_struct.copy()
            else:
                rn_wo = rn.get_text()[14:]
                rn_wo = re.sub(r'[\x92]',r"'", rn_wo)
                rn_wo = re.sub(r'[\x93-\x94]',r'"', rn_wo)
                dts_s[dts]['rn'] = rn_wo
                #print(dts, ":", hex_escape(rn_wo)
        
            #print("++++++++++++++++++++++++++++")
        dqs[query] = dts_s.copy()
    return(dqs)

def hex_escape(s):
    printable = string.ascii_letters + string.digits + string.punctuation + ' ' + '\n'
    return ''.join('' if c in printable else r'\x{0:02x}'.format(ord(c)) for c in s)

def print_dts_h(dts, dts_head):
    print ("h3. % %s, State: %s, 4ls: %s - %s" % (dts_head["type"], dts, dts_head["state"], dts_head["4ls"], \
        dts_head["title"]))

prev_release = "16.0.R7-1"
rn_resolved = "/home/hillenr/box/7750/docs/16.0/16.0.r7-1_xmlfiles/resolvedissues.xml"
rn_known = "/home/hillenr/box/7750/docs/16.0/16.0.r7-1_xmlfiles/knownissues.xml"

major = "16.0"
minor = "R8"
last_scrub = "2019/03/29"

major2subid = {
    "15.0": "127",
    "16.0": "144",
    "19.5": "152",
}

url = { 
    "res_rn_issues": "https://dts.mv.usa.alcatel.com/dts/cgi-bin/query.cgi?action=search;build_fixed=" + \
        minor + ";release_note_flag=1;reportDetail=customer_detail;subreport_id=" + major2subid[major],
    "res_cust_issues": "https://dts.mv.usa.alcatel.com/dts/cgi-bin/query.cgi?action=search;build_fixed=" + \
        minor + ";customer_id=any;reportDetail=customer_detail;subreport_id=" + major2subid[major],
    "kn_rn_issues": "https://dts.mv.usa.alcatel.com/dts/cgi-bin/query.cgi?action=search;release_note_flag_date_from=" + \
        last_scrub + ";release_note_flag=1;reportDetail=customer_detail;subreport_id=" + major2subid[major],
    "kn_cust_issues": "https://dts.mv.usa.alcatel.com/dts/cgi-bin/query.cgi?action=search;modified_date_from=" + \
        last_scrub + ";customer_id=any;reportDetail=customer_detail;subreport_id=" + major2subid[major],
    }    
dqs = parse_dts(url)
rn_cand = []
rn_res = get_resolved(rn_resolved)
rn_known = get_known(rn_known)

print("h1. Resolved issue DTS's with RN flag set:")
#print("=========================================")
print("h2. To be copied/moved from other RN sections")
#print("--------------------------------------------")
for dts in dqs["res_rn_issues"].keys():
    if dts in rn_res.keys():
        print_dts_h(dts,  dqs["res_rn_issues"][dts])
        #print ("DTS: %s, 4ls: %s" % (dts, dqs["res_rn_issues"][dts]["4ls"]))
        print("Copy from %s RNs resolved issues section *%s - %s*" % (prev_release, rn_res[dts]["rel"], rn_res[dts]["comp"]))
        print(rn_res[dts]["wu"])
        #pprint.pprint(rn_res[dts], indent=2, width=120)
    elif dts in rn_known.keys():
        print_dts_h(dts,  dqs["res_rn_issues"][dts])
        #print ("DTS: %s, 4ls: %s" % (dts, dqs["res_rn_issues"][dts]["4ls"]))
        print("Copy from %s RNs resolved issues section *%s*" % (prev_release, rn_known[dts]["comp"]))
        print(rn_known[dts]["wu"])
        #print("  Found in %s known issues:" % prev_release)
        #pprint.pprint(rn_known[dts], indent=2, width=120)
    else:
        rn_cand.append(dts)
#print()
print("h2. To be added in %s.%s RNs from DTS" % (major, minor))
#print("---------------------------------------------")
for dts in rn_cand: 
    print_dts_h(dts,  dqs["res_rn_issues"][dts])
    if dqs["res_rn_issues"][dts]["rn"]:
        #print("-----------")
        print(dqs["res_rn_issues"][dts]["rn"])
        #print()

print("h1. Resolved customer issue DTS's with RN flag not set:")
#print("===================================================")
print("h2. To be reviewed for inclusion of RN write-up")
print("----------------------------------------------")
for dts in dqs["res_cust_issues"].keys():
    if dts in dqs["res_rn_issues"].keys(): continue
    print_dts_h(dts,  dqs["res_cust_issues"][dts])
    #print("DTS: %s, 4ls: %s - %s" % (dts, dqs["res_cust_issues"][dts]["4ls"], dqs["res_cust_issues"][dts]["title"]))
    if dqs["res_cust_issues"][dts]["rn"]:
        #print("-----------")
        print(dqs["res_cust_issues"][dts]["rn"])
        #print()
    #print()

print("h1. DTS's with RN flag, updated after last release build date:")
#print("=============================================================")
print("h2. Already found in RN's")
#print("------------------------")
rn_cand = []
for dts in dqs["kn_rn_issues"].keys():
    if dts in dqs["res_rn_issues"].keys() or dts in dqs["res_cust_issues"].keys(): continue
    if dts in rn_res.keys():
        print ("%s: %s, State: %s, 4ls: %s" % (dqs["kn_rn_issues"][dts]["type"], dts, dqs["kn_rn_issues"][dts]["state"], dqs["kn_rn_issues"][dts]["4ls"]))
        print("  Found in %s resolved issues:" % prev_release)
        pprint.pprint(rn_res[dts], indent=2, width=120)
    elif dts in rn_known.keys():
        print ("%s: %s, State: %s, 4ls: %s" % (dqs["kn_rn_issues"][dts]["type"], dts, dqs["kn_rn_issues"][dts]["state"], dqs["kn_rn_issues"][dts]["4ls"]))
        print("  Found in %s known issues:" % prev_release)
        pprint.pprint(rn_known[dts], indent=2, width=120)
    else:
        rn_cand.append(dts)
print()
print("2) To be added in %s.%s RNs from DTS" % (major, minor))
print("---------------------------------------------")
for dts in rn_cand: 
    print ("%: %s, State: %s, 4ls: %s - %s" % (dqs["kn_rn_issues"][dts]["type"], dts, dqs["kn_rn_issues"][dts]["state"], dqs["kn_rn_issues"][dts]["4ls"], \
        dqs["kn_rn_issues"][dts]["title"]))
    if dqs["kn_rn_issues"][dts]["rn"]:
        print("-----------")
        print(dqs["kn_rn_issues"][dts]["rn"])
        print()
print()

print("D. Customer DTS's opened after last release build date:")
print("=======================================================")
print("1) Already found in RN's")
print("------------------------")
rn_cand = []
for dts in dqs["kn_cust_issues"].keys():
    if dts in dqs["res_rn_issues"].keys() or dts in dqs["res_cust_issues"].keys() or dts in dqs["kn_rn_issues"].keys(): continue
    if dts in rn_res.keys():
        print ("%s: %s, State: %s, 4ls: %s" % (dqs["kn_cust_issues"][dts]["type"], dts, dqs["kn_cust_issues"][dts]["state"], dqs["kn_cust_issues"][dts]["4ls"]))
        print("  Found in %s resolved issues:" % prev_release)
        pprint.pprint(rn_res[dts], indent=2, width=120)
    elif dts in rn_known.keys():
        print ("%s: %s, State: %s, 4ls: %s" % (dqs["kn_cust_issues"][dts]["type"], dts, dqs["kn_cust_issues"][dts]["state"], dqs["kn_cust_issues"][dts]["4ls"]))
        print("  Found in %s known issues:" % prev_release)
        pprint.pprint(rn_known[dts], indent=2, width=120)
    else:
        rn_cand.append(dts)
print()
print("2) Candidate known customer issues for release %s.%s" % (major, minor))
print("-------------------------------------------------------------")
for dts in rn_cand: 
    print ("%s: %s, State: %s, 4ls: %s - %s" % (dqs["kn_cust_issues"][dts]["type"], dts, dqs["kn_cust_issues"][dts]["state"], dqs["kn_cust_issues"][dts]["4ls"], \
        dqs["kn_cust_issues"][dts]["title"]))
    if dqs["kn_cust_issues"][dts]["rn"]:
        print("-----------")
        print(dqs["kn_cust_issues"][dts]["rn"])
        print()
print()
