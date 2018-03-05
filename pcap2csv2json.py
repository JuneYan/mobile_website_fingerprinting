import pickle
import os
import math
import json
import subprocess
import pandas as pd
from collections import defaultdict

def pcap2csv(pcap_file_path, csv_file_path):
        """
        extract csv file from pcap files
        Input:
            pcap_file_path: path for pcap files
            csv_file_path: path to store csv files
        
        """
        cmd = []
        cmd.append("tshark")
        cmd += ['-2','-R','tcp']  #all tcp packets
        cmd.append("-n") # dont resolve ip addresses
        cmd += "-T fields -e frame.time_epoch -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tcp.len -e tcp.flags -e tcp.analysis.out_of_order".split()
        cmd += "-Eheader=y -Eseparator=,".split() 
        cmd += ("-r %s" % pcap_file_path).split()
        print ' '.join(cmd)
        with open(csv_file_path, "w") as f:
            retcode = subprocess.call(cmd,stdout=f)
        return retcode
    
pcap_path = '/Users/junhuayan/Desktop/pcap-file-0-499/'
csv_path = '/Users/junhuayan/Desktop/mobile_dataset/cache/csv_file/2-iteration/'

for pcap in os.listdir(pcap_path):
    pcap_file_path = os.path.join(pcap_path, pcap)
    csv_file_path = os.path.join(csv_path, pcap.replace('pcap', 'csv'))
    pcap2csv(pcap_file_path, csv_file_path)
      
json_path = '/Users/junhuayan/Desktop/mobile_dataset/cache/json_file/'
visit_log_path = '/Users/junhuayan/Desktop/visti-log-345-499/'

## IP address of the mobile device
device_IP = '10.0.0.2'

for log in os.listdir(visit_log_path):
    if log == '.DS_Store': 
        continue
        
    webId = log.split('.')[0].split('_')[-1]
    csv_file = os.path.join(csv_file_path, 'web_'+webId+'_cache.csv')
    packets = pd.read_csv(csv_file, error_bad_lines=False)
    
    packets.set_index('frame.time_epoch', drop=False, inplace=True)
    if not packets.index.is_monotonic_increasing:
        packets.sort_index(inplace=True)
        
    visit_log = pd.read_pickle(os.path.join(visit_log_path, log))
    for info in visit_log:
        sample = defaultdict(list)
        if 'error' in i: 
            continue
            
        sTime, eTime= info['sTime'], info['eTime']
        url = info['url']
        tcp_connections = defaultdict(list)    
        for _, packet in packets[sTime:eTime].iterrows():
            ## filter out problematic visits
            if not math.isnan(packet['tcp.analysis.out_of_order']):
                continue 
                
            ## filter out noise
            if device_IP != packet['ip.src'] and device_IP != packet['ip.dst']:
                continue

            src_info = packet['ip.src']+':'+str(packet['tcp.srcport'])
            dst_info = packet['ip.dst']+':'+str(packet['tcp.dstport'])
            TCP_Id = '-'.join(sorted([src_info, dst_info]))

            
            length = packet['tcp.len']
            if packet['ip.src'] == device_IP:
                length*=(-1) ## < 0: outgoing packets; > 0: incoming packets

            tcp_connections[TCP_Id].append([packet['frame.time_epoch'], length, packet['tcp.flags']])

        sample_id = '-'.join([str(sTime), webId])
        sample[u'sample_id'] = sample_id
        sample[u'tcp_connection_packets'].append(tcp_connections)
        sample[u'visit_info'] = i
        with open(os.path.join(json_path, sample_id), 'w') as f:
            json.dump(sample, f)