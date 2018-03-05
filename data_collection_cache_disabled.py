import subprocess
import re
from device import Device
import time
import csv,  os
import datetime
from collections import defaultdict
import pickle

import progressbar

def get_elements(device, text, des):
    tree = device._get_current_ui_tree()
    elements = tree.findall(".//node[@%s='%s']" % (text, des))
    return elements[0]

def open_private_tab(device):
    device.tap_ui_element('resource-id','org.mozilla.firefox:id/menu')
    e = get_elements(device, 'text', 'New private tab')
    point = device._get_ui_element_center_point(e)
    device._tap(point)     
    device.tap_ui_element('resource-id','org.mozilla.firefox:id/browser_actionbar')
    
def check_fully_loaded(device):
    try:
        e = get_elements(device, 'resource-id', 'org.mozilla.firefox:id/stop')
        return False
    except:
        return True 

def get_url(device):
    url = ''
    try:
        element = get_elements(device, 'resource-id', 'org.mozilla.firefox:id/browser_toolbar')
        url = element.attrib['content-desc']
        url = url.split('?')[0]
    except:
        pass
    return url

## directory to top 1m csv files
top_1m_path = '/home/h/Desktop/dataCollection/top-1m.csv'



device_ids = Device.get_device_identifiers()
device = Device(device_ids)
top_1m_websites = []
with open(top_1m_path, "rb") as f:
    reader = csv.reader(f)
    for row in reader:
        top_1m_websites.append(row[1])
    
webnum = 500
urls = top_1m_websites[:webnum]

root_path = '/home/h/Desktop/screenshot/'
visit_path = '/home/h/Desktop/visit_log/'      

iteration = 10
bar = progressbar.ProgressBar()

for _ in bar(range(iteration)):
    
    visit_info = []
    dt_start_time = datetime.datetime.fromtimestamp(time.time())
    
    visit_info_path = os.path.join(visit_path, dt_start_time.strftime("%Y_%m_%d_%H_%M_%S_%f")+'.pickle')
    screenshot_path = os.path.join(root_path, dt_start_time.strftime("%Y_%m_%d_%H_%M_%S_%f"))
    
    if not os.path.isdir(screenshot_path):
        os.mkdir(screenshot_path)
        
    for index, url in enumerate(urls):
        try:
            info = defaultdict(list)
            device.start_package('org.mozilla.firefox')
            open_private_tab(device)
            device._enter_text(url)
            device._send_key('ENTER')
            sTime = time.time()
            while True:
                ## pages failed to load within 50s will be marked as error
                if time.time() - sTime > 50:
                    eTime = time.time()
                    a_url = get_url(device)
                    info['error']='time out'
                    device.stop_package('org.mozilla.firefox')
                    break

                if check_fully_loaded(device):
                    time.sleep(2)
                    device.take_screenshot(index, screenshot_path)
                    eTime = time.time()
                    a_url = get_url(device)
                    device.stop_package('org.mozilla.firefox')
                    break
                    
            eTime = time.time()
            info['sTime']=sTime
            info['eTime']=eTime
            info['url']=a_url
            visit_info.append(info)
        except:
            device.start_package('org.mozilla.firefox')
            device.stop_package('org.mozilla.firefox')
            pass
    
    with open(visit_info_path, 'w') as f:
        pickle.dump(visit_info, f)