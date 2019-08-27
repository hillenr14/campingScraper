'''
Created on May 14, 2016

@author: hillenr
'''
import re
import mechanize
from bs4 import BeautifulSoup
import pandas as pd
import lxml.etree as et
import requests

campings = pd.DataFrame(columns=['Names', 'URL', 'Available', ])

def get_campsites():

xml_url = "http://api.amp.active.com/camping/campgrounds?pstate=CA&siteType=2003&api_key=vr78bndc2s9a69yuaf3c35nz"
tree = et.parse(xml_url)
for line in tree.findall('result'):
    line.
    # print et.tostring(element)
    #print ''.join([child.text for child in element])
    #print ''
    element.close()
    print "xxx"
    

def RA_prep_search(location, position, date, lenghtOfStay):
    scrape_url = 'http://www.reserveamerica.com/unifSearchResults.do'
    req = mechanize.Request(scrape_url)
    req.add_header("Referer", scrape_url)
    req.add_header('user-agent', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36')
#    req.add_header("Accept-Encoding", "gzip, deflate")
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    req.add_header('Origin', 'http://www.reserveamerica.com')
    r1 = mechanize.urlopen(req)
    forms = mechanize.ParseResponse(r1)
    form =  forms[0]
    form.set_all_readonly(False)
    form['locationCriteria'] = location
    form['locationPosition'] = position
    form['interest'] = ["camping"]
    form['lookingFor'] = ['2003']
    form['camping_2003_3012'] = '3'
#    form['camping_2003_moreOptions'] = ['false']
    form['campingDate'] = date
    form['lengthOfStay'] = str(lenghtOfStay)
#    print form
    return form.click()

def prep_header_req(request):
    scrape_url = 'http://www.reserveamerica.com'
    request.add_header("Referer", scrape_url)
    request.add_header('user-agent', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36')
#    req2.add_header("Accept-Encoding", "gzip, deflate")
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    request.add_header('Origin', scrape_url)
    return mechanize.urlopen(request)

def collect_data(soup):
    camps = soup.find_all("div", {"class": "facility_view_card"})
    for camp in camps:
        print camp.find("div", {"class": "facility_view_header"}).a["title"]
        print camp.find("div", {"class": "facility_view_header"}).a["href"]
        # print camp.prettify()
        if camp.find("div", {"class": "site_types_title"}) is not None:
            print camp.find("div", {"class": "site_types_title"}).h2.contents[0]
        if camp.find("a", {"class": "book_now"}) is not None:
            print camp.find("a", {"class": "book_now"})["href"]
    
def RA_do_search(request):
    searchString1 = 'currentPage='
    searchString2 = '&paging=true&facilityType=all&agencyKey=&facilityAvailable=show_all&viewType=view_list&selectedLetter=ALL&owner=&hiddenFilters=false'
    r =  prep_header_req(request)
    soup = BeautifulSoup(r.read(), "html.parser")
    pages_str = soup.find_all("div", {"class": "usearch_results_label"})[0].contents[0].encode('ascii')
    m = re.match(r"Search Results: (\d+)-(\d+) of (\d+)", pages_str)
    pages = int(m.group(3))/(int(m.group(2)) - int(m.group(1)) + 1)
    collect_data(soup)
    for page in range(1, pages):
        searchResultURL = r.geturl() + '?' + searchString1 + str(page) + searchString2 
        req2 = mechanize.Request(searchResultURL)
        r2 =  prep_header_req(req2)
        soup = BeautifulSoup(r2.read(), "html.parser")
        print "page = " + str(page+1)
        f = open('/Users/hillenr/tmp/sample_mech.html', 'w')
        f.write(r2.read())
        f.close()
        collect_data(soup)




searchString = 'currentPage=2&paging=true&facilityType=all&agencyKey=&facilityAvailable=show_all&viewType=view_list&selectedLetter=ALL&owner=&hiddenFilters=false'

if __name__ == '__main__':
    br = mechanize.Browser()
    br.set_handle_robots(False)
    req = RA_prep_search("CALIFORNIA", '::-120.5:37.0:CA:', "Fri Jul 22 2016", 2)
    result = RA_do_search(req)
