
import xml.etree.ElementTree as ET
import re
import time
import subprocess
import os

class InstallationStepException(Exception):
    pass

class Device(object):
    def __init__(self, identifier):
        self._identifier = identifier
        self._temp_dir = os.path.join("temp",self._clean_text(self._identifier))
        
        try:
            os.makedirs(self._temp_dir)
        except:
            pass
    
    @classmethod
    def get_device_identifiers(cls):
        #identifier is needed to communicate with a device
        #we will have multiple devices connected so we need all of the ids

        output = subprocess.check_output(['adb','devices'])
        device_lines = output.splitlines()[1:] #ignore first line, it is header
        device_ids = []
        for line in device_lines:
            line=line.decode("utf-8") 
            vals = line.split('\t')
            if len(vals) > 1 and vals[1] == 'device':
                device_ids.append(vals[0])

        return device_ids
    
    def get_ip(self):
        cmd_get_device_ip = "shell dumpsys wifi | grep ip_address"
        output = self._get_adb_cmd_output(cmd_get_device_ip)
        m = re.search("\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}",output)

        return m.group() if m else ""
    
    def _clean_text(self, text):
        return re.sub(r'[^a-zA-Z0-9]+','', text)
    
    def _run_adb_cmd(self, cmd):
        try:
            cmd = ["adb","-s",self._identifier]+cmd.split()
#             print " ".join(cmd)
            subprocess.check_call(cmd)
        except Exception as e:
            raise InstallationStepException(str(e))   
            
    def _get_adb_cmd_output(self, cmd):
        try:
            cmd = ["adb","-s",self._identifier]+cmd.split()
#             print " ".join(cmd)
            return subprocess.check_output(cmd)
        except Exception as e:
            raise InstallationStepException(str(e))   

    def download_file(self, file_path, output_file_path):
        self._run_adb_cmd("pull %s %s" % (file_path, output_file_path))
          
    def start_package(self, package):
        """
        hack to start an app using package name:
        use monkey tool and send 1 random action which is starting the app
        http://stackoverflow.com/questions/4567904/how-to-start-an-application-using-android-adb-tools
        """
        cmd = "shell monkey -p %s -c android.intent.category.LAUNCHER 1" % package
        
        self._run_adb_cmd(cmd)
    
    def stop_package(self, package):
        cmd = "shell am force-stop "+package
        self._run_adb_cmd(cmd)
        
    
    def get_3_party_package_names(self):
        output = self._get_adb_cmd_output("shell pm list package -3")
        package_names = output.splitlines()
        package_names = [name[8:] for name in package_names]
        return package_names

    def install_package(self, app_name, package_file_path):
        self._run_adb_cmd('install %s' % package_file_path)
        installed_package_names = self.get_3_party_package_names()
        if app_name in installed_package_names:
            return True
        else:
            return False

    def take_screenshot(self, uID, output_file_path):
        filename = 'screenshot_'+str(uID)+'.png'
        self._run_adb_cmd("shell screencap -p /sdcard/%s" %filename)
        self._run_adb_cmd("pull /sdcard/%s %s" % (filename, output_file_path))
        
    def download_package(self,package_name, output_dir):
        apk_path = self._get_adb_cmd_output("shell pm path "+package_name)[8:].strip()
        self._run_adb_cmd('pull '+apk_path+" "+output_dir)
        
    def download_3_party_apps(self, output_dir):
        package_names = self.get_3_party_package_names()
        for package in package_names:
            self.download_package(package, output_dir)
        
    def uninstall_package(self, package):
        self._run_adb_cmd('shell pm uninstall %s' % package)
        
    def uninstall_3_party_apps(self):
        package_names = self.get_3_party_package_names()
        for package in package_names:
            self.uninstall_package(package)
            
    def is_package_running(self, package):
        output = self._get_adb_cmd_output("shell ps | grep %s" % package)
        return True if output else False
    
    def _enter_text(self, text):
        text = text.replace(' ','%s')
        self._run_adb_cmd("shell input text %s" % text)

    def _send_key(self, key):
        self._run_adb_cmd("shell input keyevent KEYCODE_%s" % key)
        
    
    
    def _get_current_ui_tree(self, compressed=True):

        """
        - ui.xml is saved in temp/ui.xml, open in browser to examine
        - will fail if the UI is changing frequently 
        (e.g., a banner using javascript or a music player with a progress bar)
        uiautomator dump fails if the UI is changing frequently.

        https://code.google.com/p/android/issues/detail?id=58987
        https://android.googlesource.com/platform/frameworks/testing/+/jb-mr2-release/uiautomator/cmds/uiautomator/src/com/android/commands/uiautomator/DumpCommand.java
        uiAutomation.waitForIdle timeouts
        AccessibilityNodeInfoDumper.java
        """
        ui_xml_file_name = "ui.xml"
        ui_xml_file_path = os.path.join(self._temp_dir,ui_xml_file_name)
        self._run_adb_cmd("shell uiautomator dump %s /sdcard/%s" % ("--compressed" if compressed else "", ui_xml_file_name))
        self._run_adb_cmd("pull /sdcard/ui.xml "+ui_xml_file_path)
        return ET.parse(ui_xml_file_path)

    def _get_ui_element(self, tree, attribute, value):
        """use uiautomatorviewer to find attribute,value pair of an element"""
        elements = tree.findall(".//node[@%s='%s']" % (attribute, value)) 
        return elements[0]
    
    def ui_element_exists(self, attribute, value):
        tree = self._get_current_ui_tree()
        elements = tree.findall(".//node[@%s='%s']" % (attribute, value)) 
        return True if len(elements) > 0 else False
    
    def _get_clickable_ui_elements(self):
        """returns clickable elements on the current UI"""
        tree = self._get_current_ui_tree()
        elements = tree.findall(".//")
        clickable_elements = []
        for e in elements:
            if e.get('clickable') == 'true':
                clickable_elements.append(e)
        return clickable_elements
    
    def _get_ui_element_center_point(self, element):
        """return center point of a UI element calculated from the element's bounds.

        returns a tuple (x,y)
        """
        s = element.get('bounds')
        m = re.search("\[(\d+),(\d+)\]\[(\d+),(\d+)\]",s)
        (x1,y1,x2,y2) = [int(c) for c in m.groups()]
        return ((x1+x2)/2, (y1+y2)/2)

    def _get_coordinates(self, attribute, value):
        t = self._get_current_ui_tree()
        e = self._get_ui_element(t, attribute, value)
        p = self._get_ui_element_center_point(e)
        return p
    
    def tap_ui_element(self, attribute, value):
        t = self._get_current_ui_tree()
        e = self._get_ui_element(t, attribute, value)
        p = self._get_ui_element_center_point(e)
        self._tap(p)

    def _tap(self, point):
        """tap touchscreen at the given point.
        point -- (x,y) 
        """
        self._run_adb_cmd("shell input tap %s %s" % point)
        
    def _verify_ui_element(self, key, value, timeout, polling_interval=2):
        wait_threshold = timeout
        start_time = time.time()
        wait_duration = 0
        
        element = None
        while(wait_duration < wait_threshold):
            try:
                element = self._get_ui_element(self._get_current_ui_tree(),key, value)
                break
            except:
                time.sleep(polling_interval)
            wait_duration = (time.time()-start_time)

        if element is None:
            return False
        else:
            return True