'''
Created on May 14, 2016

@author: hillenr
'''
import re
import mechanize
from bs4 import BeautifulSoup
import pandas as pd
import lxml.etree as et
from math import radians, cos, sin, asin, sqrt, atan2, degrees
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os.path,argparse
import sched, time, datetime

def get_campsites(location):
    xml_url = "http://api.amp.active.com/camping/campgrounds?pstate=CA&siteType=2003&api_key=vr78bndc2s9a69yuaf3c35nz"
    tree = et.parse(xml_url)
    cs=pd.DataFrame()
    for line in tree.findall('result'):
        cs = cs.append(pd.DataFrame(dict(line.attrib),index=[line.attrib.values()[5]]))
    cs = cs.drop(cs.columns[[0, 1, 2, 5, 7, 10, 11, 13, 14, 15, 16]], axis=1)
    cs[['latitude', 'longitude']] = cs[['latitude', 'longitude']].apply(lambda x: pd.to_numeric(x, errors='coerce'))
    cs['Distance'] = cs.apply(lambda x: haversine(location[1], location[0], x.longitude,x.latitude)[0], axis=1)
    cs['Bearing'] = cs.apply(lambda x: haversine(location[1], location[0], x.longitude,x.latitude)[1], axis=1)
    # cs['index1'] = cs.index
    cs.index = 'I' + cs.index
    return cs
    
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    Bearing =atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1)) 
    Bearing = degrees(Bearing)
    if Bearing < 0: Bearing += 360
    return [km, Bearing]

def RA_prep_search(location, position, date, lenghtOfStay, accessNeeds=False):
    scrape_url = 'http://www.reserveamerica.com/unifSearchResults.do'
    req = mechanize.Request(scrape_url)
    req.add_header("Referer", scrape_url)
    req.add_header('user-agent', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36')
#    req.add_header("Accept-Encoding", "gzip, deflate")
    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    req.add_header('Origin', 'http://www.reserveamerica.com')
    r1 = mechanize.urlopen(req)
    forms = mechanize.ParseResponse(r1, backwards_compat=False)
    form =  forms[0]
    form.set_all_readonly(False)
    form['locationCriteria'] = location
    form['locationPosition'] = position
    form['interest'] = ["camping"]
    form['lookingFor'] = ['2003']
    form['camping_2003_3012'] = '3'
#    print form
#    control = form.find_control("camping_2003_3009")
#    for item in control.items:
#        print " name=%s values=%s" % (item.name, str([label.text  for label in item.get_labels()]))
#    return
    if accessNeeds:
        form['camping_2003_moreOptions'] = ['true']
        form['camping_2003_3009'] = ['true']
    else:
        form['camping_2003_moreOptions'] = []
        form['camping_2003_3009'] = []
    form['campingDate'] = date
    form['lengthOfStay'] = str(lenghtOfStay)
    return form.click()

def prep_header_req(request):
    scrape_url = 'http://www.reserveamerica.com'
    request.add_header("Referer", scrape_url)
    request.add_header('user-agent', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36')
#    req2.add_header("Accept-Encoding", "gzip, deflate")
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    request.add_header('Origin', scrape_url)
    return mechanize.urlopen(request)

def collect_data(soup, campings):
    camps = soup.find_all("div", {"class": "facility_view_card"})
    for camp in camps:
        name = camp.find("div", {"class": "facility_view_header"}).a["title"]
        link = camp.find("div", {"class": "facility_view_header"}).a["href"]
        id = re.search(r'(\d{5,7})$', link).group(1)
        id = "I" + id
        # print id
        # print camp.prettify()
        if camp.find("div", {"class": "site_types_title"}) is not None:
            space_str = camp.find("div", {"class": "site_types_title"}).h2.contents[0]
            spaces = int(re.search(r'^(\d+)', space_str).group(1))
            # print spaces
        else:
            spaces = 0
        # if camp.find("a", {"class": "book_now"}) is not None:
            # print camp.find("a", {"class": "book_now"})["href"]
        data = {'Name': name, 'Spots': spaces, 'Link': link}
        campings = campings.append(pd.DataFrame(data, index= [id]))
    return campings

def RA_do_search(request):
    campings = pd.DataFrame()
    searchString1 = 'currentPage='
    searchString2 = '&paging=true&facilityType=all&agencyKey=&facilityAvailable=show_all&viewType=view_list&selectedLetter=ALL&owner=&hiddenFilters=false'
    r =  prep_header_req(request)
    soup = BeautifulSoup(r.read(), "html.parser")
    # print soup
    pages_str = soup.find_all("div", {"class": "usearch_results_label"})[0].contents[0].encode('ascii')
    m = re.match(r"Search Results: (\d+)-(\d+) of (\d+)", pages_str)
    pages = int(m.group(3))/(int(m.group(2)) - int(m.group(1)) + 1)
    campings = collect_data(soup, campings)
    for page in range(1, pages):
        searchResultURL = r.geturl() + '?' + searchString1 + str(page) + searchString2 
        req2 = mechanize.Request(searchResultURL)
        r2 =  prep_header_req(req2)
        soup = BeautifulSoup(r2.read(), "html.parser")
        print page+1,
        # f = open('/Users/hillenr/tmp/sample_mech.html', 'w')
        # f.write(r2.read())
        # f.close()
        campings = collect_data(soup,campings)
    print
    return campings

def send_email(newSpots, email_subj):
    pd.options.display.max_colwidth = 200
    LOGIN = 'hillenr'
    PASSWORD = 'Nathan@150'
    me = "hillenr@gmail.com"
    you = "hillenr@gmail.com"
    
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = email_subj
    msg['From'] = me
    msg['To'] = you
    text = ""
    for dl in newSpots.keys():
        text += "<h3>Date: " + dl[0] + " for " + str(dl[1]) + " days.</h3>\n" + \
            newSpots[dl].to_html(escape=False, index=False)
    html = """\
    <html>
      <head></head>
      <body>
        %s
      </body>
    </html>
    """ % text
    msg.attach(MIMEText(html, 'html'))
    
    # Send the message via local SMTP server.
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(LOGIN, PASSWORD)
    server.sendmail(me, you, msg.as_string())
    server.quit()

def email_newspots(date_len, location, distance, doall):
    print datetime.datetime.today().strftime('%Y/%m/%d %H:%M:%S')
    # csa_path = '/Users/hillenr/Dropbox/Developer/workspace/WebScraper/'
    cs_path = ''
    cs = get_campsites(location)
    ns = {}
    for dl in date_len:
        req = RA_prep_search("CALIFORNIA", '::-120.5:37.0:CA:', *dl)
        csa = RA_do_search(req)
        fn = cs_path + 'Spot_' + dl[0] + '.csv'
        if not os.path.isfile(fn) or doall:
            ft = 'ever'
            req_a = RA_prep_search("CALIFORNIA", '::-120.5:37.0:CA:', *dl, accessNeeds=True)
            csa_a = RA_do_search(req_a)
            cs['Spots_tot'] = csa.Spots
            cs['Spots_acc'] = csa_a.Spots
            cs[['Spots_tot', 'Spots_acc']] = cs[['Spots_tot', 'Spots_acc']].fillna(0)
            cs['Spots'] = cs.Spots_tot - cs.Spots_acc
            newSpots = cs[(cs.Distance < distance) & (cs.Spots >0)][['facilityName', 'Spots']]
        else:
            ft = time.ctime(os.path.getmtime(fn))
            csa_a = pd.read_csv(fn,dtype={0:object})
            csa_a = csa_a.set_index('Unnamed: 0')
            cs['Spots'] = csa_a.Spots.astype(int)
            cs['SpotsNew'] = csa.Spots.astype(int)
            newSpots = cs[(cs.Spots < cs.SpotsNew) & (cs.Distance < distance)][['facilityName', 'Spots', 'SpotsNew']]
        print pd.concat([newSpots, cs[['Distance', 'Bearing']]], axis=1, join='inner')
        if len(newSpots > 0):
            newSpots['Link'] = cs.apply(lambda x:
                '<a href="http://www.reserveamerica.com/unifSearchInterface.do?interface=bookcamp&contractCode='
                + x.contractID + '&parkId=' + x.index1 + '">Book</a>', axis = 1)
            newSpots['Location'] = cs.apply(lambda x:
                '<a href="http://maps.google.com/maps?z=10&t=m&q=loc:' + str(x.latitude) + '+' + str(x.longitude) +
                '">[' + '{:4.0f}'.format(x.Distance) + ',' + '{:4.0f}'.format(x.Bearing) + ']</a>', axis =1)
            newSpots['facilityName'] = csa.apply(lambda x:
                '<a href="http://www.reserveamerica.com' + x.Link + '">' + x.Name + '</a>', axis =1)                    
            ns[dl] = newSpots
        csa.to_csv(fn)
    if bool(ns):
        send_email(ns, "New camping sites since " +  ft)

def email_newspots1(date_len, location, distance, doall):
    now = datetime.datetime.today().strftime('%Y/%m/%d %H:%M')
    print now
    # csa_path = '/Users/hillenr/Dropbox/Developer/workspace/WebScraper/'
    cs_path = ''
    fn = cs_path + 'campings_CA.xlsx'
    c_sites = get_campsites(location)
    ns = {}
    dfs = {}
    if os.path.isfile(fn):
        xl = pd.ExcelFile(fn)
        dfs = {sheet: xl.parse(sheet, convertors={0: str}) for sheet in xl.sheet_names}
    for dl in date_len:
        sheet = dl[0] + " " + str(dl[1])
        cs = c_sites.copy()
        req = RA_prep_search("CALIFORNIA", '::-120.5:37.0:CA:', *dl)
        csa = RA_do_search(req)
        req_a = RA_prep_search("CALIFORNIA", '::-120.5:37.0:CA:', *dl, accessNeeds=True)
        csa_a = RA_do_search(req_a)
        cs[['Distance', 'Bearing']] = cs[['Distance', 'Bearing']].fillna(0, axis=1)
        cs['Spots_tot'] = csa.Spots
        cs['Spots_acc'] = csa_a.Spots
        cs[['Spots_tot', 'Spots_acc']] = cs[['Spots_tot', 'Spots_acc']].fillna(0, axis = 1)
        cs[now] = cs.Spots_tot - cs.Spots_acc
        if not sheet in dfs or doall:
            ft = 'ever'
            newSpots = cs[(cs.Distance < distance) & (cs[now] > 0)][['facilityName', now]]
        else:
            csf = dfs[sheet]
            timestamps=[]
            for col in list(csf.columns.values):
                m = re.match(r"(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2})", col)
                if not m is None:
                    timestamps.append(datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))))
            if len(timestamps) >= 1:
                max_ts = max(timestamps).strftime("%Y/%m/%d %H:%M")
                ft = max_ts
                cs[max_ts] = csf[max_ts]
                newSpots = cs[(cs[max_ts] < cs[now]) & (cs.Distance < distance)][['facilityName', max_ts, now]]
            else:
                ft = 'ever'
                newSpots = cs[(cs.Distance < distance) & (cs[now] > 0)][['facilityName', now]]                
        # cs = cs.drop(['latitude', 'longitude', 'Distance', 'Bearing'], axis=1)                   
        print pd.concat([newSpots, cs[['Distance', 'Bearing']]], axis=1, join='inner')
        if len(newSpots > 0):
            cs['index1']=cs.index
            newSpots['Link'] = cs.apply(lambda x:
                '<a href="http://www.reserveamerica.com/unifSearchInterface.do?interface=bookcamp&contractCode='
                + x.contractID + '&parkId=' + x.index1[1:] + '">Book</a>', axis = 1)
            newSpots['Location'] = cs.apply(lambda x:
                '<a href="http://maps.google.com/maps?z=10&t=m&q=loc:' + str(x.latitude) + '+' + str(x.longitude) +
                '">[' + '{:4.0f}'.format(x.Distance) + ',' + '{:4.0f}'.format(x.Bearing) + ']</a>', axis =1)
            newSpots['facilityName'] = csa.apply(lambda x:
                '<a href="http://www.reserveamerica.com' + x.Link + '">' + x.Name + '</a>', axis =1)                    
            ns[dl] = newSpots
            cs = cs.drop('index1',axis=1)
        cs['Distance'] = cs.apply(lambda x:
            '=HYPERLINK("http://maps.google.com/maps?z=10&t=m&q=loc:' + str(x.latitude) + '+' + str(x.longitude) +
            '", ' + str(int(x.Distance)) + ')', axis = 1)
        cs['Bearing'] = cs.apply(lambda x: int(x.Bearing), axis=1)
        cs['facilityName'] = csa.apply(lambda x:
            '=HYPERLINK("http://www.reserveamerica.com' + x.Link + '", "' + x.Name + '")', axis =1)
        dfs[sheet] = cs
    with pd.ExcelWriter(fn) as writer:
        for key in dfs.keys():
            dfs[key].to_excel(writer,sheet_name=key)
        writer.save()
    if bool(ns):
        send_email(ns, "New camping sites since " +  ft)


def print_time(date_len, distance):
     print date_len
     print distance
     print datetime.datetime.today()
 

def conv_date(inp_date):
    m = re.match(r"(\d+)/(\d+)/(\d+)", inp_date)
    if m is None:
        return None
    date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return date.strftime("%a %b %d %Y")

def get_args():
    parser = argparse.ArgumentParser(description='Find free camping spots at reserveamerica.com')
    parser.add_argument('dates', metavar='date', nargs='+',
                        help='list of dates')
    parser.add_argument('--days', action='store', type=int, default=2,
                        help='number of days (default: 2)')
    parser.add_argument('--start', action='store', type=int, default=8,
                        help='scan daily start hour (default: 8)')
    parser.add_argument('--stop', action='store', type=int, default=23,
                        help='scan daily stop hour (default: 23)')
    parser.add_argument('--interval', action='store', type=int, default=3,
                        help='scan interval in hours (default: 3)')
    parser.add_argument('--lat', action='store', type=float, default=37.327699,
                        help='location center lattitude (default: San Jose location)')
    parser.add_argument('--long', action='store', type=float, default=-121.906100,
                        help='location center longitude (default: San Jose location)')
    parser.add_argument('--distance', action='store', type=int, default=300,
                        help='distance from location center in km (default: 300)')
    parser.add_argument('--now', action='store', type=int, default=300,
                        help='distance from location center in km (default: 300)')
    args = parser.parse_args()
    date_len = []
    for date_inp in args.dates:
        date_len.append((conv_date(date_inp), args.days))
    times = range(args.start, args.stop+1, args.interval)
    location = [args.lat, args.long]
    return (date_len, times, location, args.distance)
    

if __name__ == '__main__':
    (date_len, times, location, distance) = get_args()
    br = mechanize.Browser()
    br.set_handle_robots(False)
    email_newspots1(date_len, location, distance, False)
    d = datetime.date.today()
    s = sched.scheduler(time.time, time.sleep)
    while True:
        for t in times:
            t1 = datetime.time(t)
            dt = datetime.datetime.combine(d,t1)
            time_stamp = time.mktime(dt.timetuple())
            if time_stamp > time.time():
                s.enterabs(time_stamp, 1, email_newspots1, (date_len, location, distance, False))
        s.run()
        d += datetime.timedelta(days=1)

