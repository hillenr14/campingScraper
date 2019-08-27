'''
Created on May 13, 2016

@author: hillenr
'''
import requests

scrape_url = 'http://www.reserveamerica.com/unifSearchResults.do'

payload = {'locationCriteria': 'CALIFORNIA',
           'locationPosition': '::-120.5:37.0:CA:',
           'interest': 'camping', 
           'currentMaximumWindow': '12',
           'contractDefaultMaxWindow': 'MS:24,LT:18,GA:24,SC:13,PA:24',
           'stateDefaultMaxWindow': 'MS:24,GA:24,SC:13,PA:24',
           'defaultMaximumWindow': '12',
           'lookingFor': '2003',
           'camping_2003_3012': '3',
           'campingDate': 'Fri Jul 22 2016',
           'lengthOfStay': '2',
           'dayUseDate': 'Fri Jul 22 2016',
           'dayUseLengthOfStay': '2'}

headers = {'user-agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36',
           'referer': scrape_url}

if __name__ == '__main__':
    r = requests.post(scrape_url, data=payload, allow_redirects = True, headers = headers)
    print(r.url)
    f = open('/Users/hillenr/tmp/sample.html', 'w')
    f.write(r.text)
    f.close()
    print(r.history)