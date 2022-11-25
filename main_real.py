import argparse
import json
import time
import socket
from socket import AF_INET, SOCK_DGRAM
from pynput.keyboard import Key, Listener, Controller,Events
import threading
import random

import traceback

from simul import run_file 

# เวลาใช้ thread เหมือนกับว่ารันโปรแกรมหลายๆ window พร้อมๆกัน 
# global คือ global ของแต่ละ window

local_dict = {} # routing table ของตัวเอง มีการปรับเปลี่ยนไปหลังจากได้รับข้อมูลมาจาก neighbor router
org_local_dict = {}
node_name = ''
neighbour_addr = []
output_dict = {}
# port_table = {}
port_table = {}

global round
round = -1

# Description: command ไว้ทำตามคำสั่ง
def _argparse():
    # print('parsing args...')
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", "-node_name", default='', help="node name") 
    parser.add_argument("--add", "-add_node_name", default='', help="add node name")
    parser.add_argument("--delete", "-delete_node_name", default='', help="delete node name")
    parser.add_argument("--change", "-change_cost", default='', help="change cost") # Description: ใช้เมื่อต้องการเปลี่ยน link cost
    arg = parser.parse_args()
    return arg
 # Description: print routing table format   
def print_routing_table(node_name,round,output_dict):
    output_table = ''
    output_table += 'At Router '+str(node_name)+', t = '+str(round)+'\n'
    output_table += 'Dest. Subnet | Next hop |Cost'+'\n'
    output_table += '--------------------------------'+'\n'
    for key in dict(output_dict).keys():
        if(key.find('N') != -1):
            output_table += str(key)+'           |   '+str(output_dict[key]['next_hop'])+'    |'+str(output_dict[key]['distance'])+'\n'
    output_table += '--------------------------------\n\n'
    print(output_table)

# description: ฟังข่าวจากเพื่อนบ้านมาใช้ rip
def listen_to_news_from_neighbours():
    global node_name
    global local_dict
    global org_local_dict
    global neighbour_addr
    global output_dict
    global port_table
    global round
    start_time = time.time() #เวลาที่เริ่มต้นรับข้อมูล
    # print(node_name + ' starts listening distance vector from peer nodes...')
    while True:
        try: # รอ router อื่นมา connect เพราะตอนแรกจะเจอ error [WinError 10054] An existing connection was forcibly closed by the remote host
            peer_info_b, peer_addr = localInfo_socket.recvfrom(10248) # Description: server process รับข้อมูลจากที่ส่งในฟังก์ชั่น update_news_to_neighbours
            # description: กรณี Hello message
            if((peer_info_b.decode()).find('HELLO') != -1):
                alive_node = (peer_info_b.decode()).split(' ') # description: แยกชื่อ router ออกจาก message
                port_table[alive_node[0]]["alive"] = time.time() # description: set เวลา alive ใหม่
                print(peer_info_b.decode()) # description: print hello message
            # description: กรณี update message
            else:
                peer_info_split = (peer_info_b.decode()).split('->') # description: แยกชื่อ router ออกจาก routing table
                peer_node = peer_info_split[0] # Description: รับข้อมูลชื่อ neighbor node (จาก update_news_to_neighbours คือชื่อ node)
                peer_dv = peer_info_split[1] # Description: รับข้อมูลระยะทางไป neighbor node (จาก update_news_to_neighbours คือ cost)
                peer_dict = eval(peer_dv) # Description: ทำให้ cost กลับไปเป็นรูปแบบ json อีกครั้ง (ใช้ eval เพราะรูปแบบที่รับเข้ามาไม่ใช่ json แล้วใช้ json.load ไม่ได้)
                # description: if node that send information is not in neighbor list add its information
                if((not peer_addr in neighbour_addr) or (not peer_node in org_local_dict.keys())): # description: ไม่มีข้อมูล ip ใน port หรือ ไม่มีชื่อ router ใน routing table
                    # print('add router --------------->')
                    if(peer_node != node_name): # ถ้า node ที่ส่งข้อมูลมาไม่ใช่ router ตัวเอง
                        add_router(peer_node,peer_addr,peer_dict)

                # description: If there are keys in the neighbour that local dict does not have
                # description: add them, and update the distance to infinity
                for neighbour_key in peer_dict: # Description: วนใน neighbor node
                    # Description: จากข้อมูลที่ได้รับจาก neighbor node ถ้าเจอ router ที่ไม่ใช่เพื่อนบ้านและไม่ใช่เราเอง ให้ set เป็นค่าสูงสุดไว้ก่อน (เพราะยังไม่รู้ทางไป)
                    if (not neighbour_key in local_dict.keys() and neighbour_key != node_name): 
                        local_dict[neighbour_key] = 16 # Description: เพิ่ม node ใหม่ไปใน routing table ของตัวเอง

                # Recompute distance vector, if the distance from peer to location is smaller, refresh the distance vector
                for key in dict(local_dict).keys(): # Description: วนตรวจสอบระยะทางที่จะไปหา neighbor ที่สั้นที่สุด
                    next_hop = key # Description: next-hop คือ neightbor router
                    distance = local_dict[key] # Description: distance ปัจจุบัน
                    distance1 = local_dict[key] # Description: เอาไว้เช็คว่า distance ต่างจากเดิมไหม จะได้ output update ออกมา

                    # If currently checked key is the same as peer_node name, then update the distance to 0
                    if key == peer_node: #Description:  ที่ router ตัวเอง
                        peer_dict[key] = 0 # Description: มี distance = 0 (อยู่ที่เดิม ไม่ได้ไปไหน)
                    # If the currently checked key is not in the dictionary of peer's, update the value to infinite
                    if not key in peer_dict.keys(): # Description: ถ้าเป็น router node ที่ไม่มีในข้อมูลจาก neighbor แสดงว่ายังไปไม่ถึง
                        peer_dict[key] = 16 # Description: เนื่องจากไปไม่ถึงจึงต้อง set ค่าสูงสุดไว้ก่อน

                    # description: วนอัพเดตค่า routing table ถ้ามี cost เปลี่ยน
                    for link_key in output_dict.keys():
                        for info_key in peer_dict.keys():
                            # check หา routing table ที่มี dest. ตรงกับ ข้อมูลจากเพื่อนบ้าน และ มี next_hop ตรงกับ router ที่ส่งข้อมูลมา และ ค่าที่บวกเพิ่มไม่เกิน max hop
                            if(info_key == link_key and output_dict[link_key]['next_hop'] == peer_node and peer_dict[info_key] + local_dict[peer_node] < 16):
                                if(output_dict[link_key]['distance'] != peer_dict[info_key] + local_dict[peer_node]): # description: ถ้า cost เปลี่ยน
                                    output_dict[link_key]['distance'] = peer_dict[info_key] + local_dict[peer_node] # description: update cost(ต้นทาง,ปลายทาง) = cost(เพื่อนบ้าน,ปลายทาง)ใหม่ + cost(ต้นทาง,ปลายทาง)เดิม
                                    local_dict[link_key] = output_dict[link_key]['distance'] # description: update routing table
                                    round = round + 1 # description: นับจำนวนรอบ
                                    print_routing_table(node_name,round,output_dict) # description: print routing table
                                    update_news_to_neighbours(neighbour_addr, node_name, local_dict) # description: เข้าขั้นตอน ส่ง + ฟัง
                    # description: ถ้าค่า(ตัวเอง,ปลายทาง) มากกว่า ค่า(ตัวเอง,เพื่อนบ้าน) + ค่า(เพื่อนบ้าน,ปลายทาง) และ เป็นปลายทางใหม่ที่ไม่มีใน routing table ต้นฉบับ และค่าที่เดินทางผ่านน้อยกว่า max hop
                    if local_dict[key] > peer_dict[node_name] + peer_dict[key] and peer_node in org_local_dict.keys() and peer_dict[node_name] + peer_dict[key] < 16:
                        # local_dict[key] = 16 # Description: poison reverse
                        # update_news_to_neighbours(neighbour_addr, node_name, local_dict) # Description: poison reverse 
                        local_dict[key] = peer_dict[node_name] + peer_dict[key] #Description: update ระยะทางให้สั้นลงจากเดิม
                        next_hop = peer_node # Description: ต้องผ่าน neighbour ตัวไหนถึงจะไปถึง
                        distance1 = peer_dict[node_name] + peer_dict[key] # Description: เก็บค่า distance ใหม่เอาไว้เช็คว่าจะ output ไหม
                        update_news_to_neighbours(neighbour_addr, node_name, local_dict) # Description: ส่ง routing table ที่ update ให้เพื่อนบ้าน
                    # Description: If the distance and next_hop both changed, update the output distance vector
                    if (distance != distance1): # Description: check ว่า distance เปลี่ยนแปลงไหม ถ้าเปลี่ยน update ใน dict ที่เป็น format ไว้ output
                        output_dict.update({key: {"distance": local_dict[key], "next_hop": next_hop}}) # Description: function update เอาไว้เพิ่ม/แก้ไขค่าตามkey ใน dict
                        with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'w+') as output: # Description: update ค่าไว้ debug
                            output.write(json.dumps(output_dict))
                        # Description: new print format
                        round = round + 1 # Description: นับจำนวนรอบ
                        print_routing_table(node_name,round,output_dict) # Description: print routin table
                        
                        # time.sleep(2)

                end_time = time.time() # Description: เวลาที่สิ้นสุดการรับข้อมูล
                # If there are no more updates in the local dict and the result converges, write the final jason file
                if end_time - start_time > 20: # ถ้าเวลาผ่านไป 20 s แล้วทำการเขยนข้อมูลลงไปใน json
                    with open('routing_table/'+node_name +'/'+node_name+ '_output.json', 'w+') as output:
                        output.write(json.dumps(output_dict))

        except Exception as e:
            # print('except: ',str(e)+'\n')
            # print(traceback.format_exc())
            if(str(e).find('WinError 10054') != -1): # Description: เมื่อไม่สามารถส่งถึง router เพื่อนบ้านได้ 
                # print('neighbor router is down')
                delete_key = [] # Description: เอาไว้เก็บ router ที่ไม่ตอบสนองเกินเวลา
                delete_neighbor_path = [] # Description: เอาไว้เก็บเพื่อนบ้านของ router ที่ไม่ตอบสนองเกินเวลา
                for org_neighbor_node in org_local_dict.keys(): # Description: วนใน router ดั้งเดิม (direct link)
                    if(org_neighbor_node.find('N') == -1): # Description: ไม่ใช่ network
                        # print(org_neighbor_node ,": time now => ",time.time() - port_table[org_neighbor_node]["alive"])
                        if(time.time() - port_table[org_neighbor_node]["alive"] > 25): # Description: ไม่ตอบสนองนานเกิน 25 s
                            delete_key.append(org_neighbor_node) # Description: เก็บ router ที่ไม่ตอบสนองนานเกินกำหนด
                            for key in output_dict.keys():
                                if(output_dict[key]['next_hop'] == org_neighbor_node): # Description: check ว่า ปลายทางต้องเดินผ่าน router ที่ไม่ตอบสนอง
                                    delete_neighbor_path.append(key)# Description: เก็บ ปลายทาง ที่ต้องเดินทางผ่าน router ที่ไม่ตอบสนองนานเกินกำหนด
                # Description: วนลบ router ที่ไม่ตอบสนอง ลบ [routing table, routing table (direct link), ip address]
                for key in delete_key:
                    del local_dict[key]
                    del org_local_dict[key]
                    address_del_key = port_table[key]['address']
                    del port_table[key]
                    neighbour_addr.remove(address_del_key)
                # Description: ลบข้อมูลปลายทางที่ต้องเดินผ่าน router ที่ไม่ตอบสนอง ลบ [routing table, routing table (direct link)]
                for neighbor_path in delete_neighbor_path:
                    del local_dict[neighbor_path]
                    del output_dict[neighbor_path]
                with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'w+') as new_distance: # Description: เก็บข้อมูลไว้ debug
                    new_distance.write(json.dumps(local_dict))
                # print('new local_dict in not response: ',local_dict)
                start_routing(neighbour_addr, node_name, local_dict) # Description: เข้าขั้นตอนการ ส่ง + ฟัง
            # Description: ถ้าไม่ใช่ error จากส่งไม่ถึงเพื่อนบ้าน
            else:
                time.sleep(10)
                check_port() # Description: ตรวจสอบค่า cost direct link ว่ายังเท่าเดิมอยู่ไหม
                end_time = time.time()
                #
                if end_time - start_time > 20: #
                    with open('routing_table/'+node_name +'/'+node_name+ '_output.json', 'w+') as output:
                        output.write(json.dumps(output_dict))
                    print("Time out, program exits.")
                    break
    
# description: check routing table ดั้งเดิมมีการเปลี่ยนแปลงไหม (กรณี เปลี่ยนค่า cost)
def check_port():
    global local_dict
    global org_local_dict
    global node_name
    global neighbour_addr
    global output_dict
    global port_table
    global round
    have_new_data  = False
    # description: check distance
    with open('routing_table/'+node_name +'/'+node_name+ '_distance.json', 'r') as f:
        new_dict = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
    # description: update direct link
    update_node = []
    for key in new_dict.keys():
        if(key in org_local_dict.keys()): # description: check ว่า key ที่อ่านมาอยู่ใน routing table ดั้งเดิมไหม
            if(new_dict[key] != org_local_dict[key]): # description: ถ้าค่าที่อ่านมาไม่ตรงกับที่มีอยู่
                local_dict[key] = new_dict[key] # description: update เป็นค่าใหม่ที่อ่านเข้ามา (ลง routing table ที่มีการเปลี่ยนแปลง)
                org_local_dict[key] = new_dict[key] # description: update เป็นค่าใหม่ที่อ่านเข้ามา (ลง routing table ดั้งเดิม)
                output_dict[key]["distance"] = new_dict[key] # description: update เป็นค่าใหม่ที่อ่านเข้ามา (ลง routing table ที่เป็น output)
                have_new_data = True # description: มีค่าใหม่
                with open('routing_table/'+node_name +'/'+node_name+ '_distance.json', 'w') as new_distance: # description: update routing table ใหม่ลงไฟล์ดั้งเดิม
                    new_distance.write(json.dumps(org_local_dict))
                update_node.append(key) # description: เก็บค่า router ที่มีการ update
    # description: update neighbor of change link (next hop)
    for update_key in update_node:
        if(update_key.find('N') == -1): # description: check ว่าไม่ใช่ network (network เป็น next hop ไม่ได้)
            for key in output_dict.keys():
                if(output_dict[key]['next_hop'] == update_key):# description: ถ้าเป้น next hop ที่มีการ update cost ใหม่
                    output_dict[key]['distance'] = output_dict[key]['distance'] + local_dict[update_key] # description: [output ใช้ print] update cost(ตัวเอง,ปลายทาง) = cost(เพื่อนบ้าน,ปลายทาง)เดิม + cost(ตัวเอง,เพื่อนบ้าน)ใหม่ 
                    local_dict[key] = local_dict[key] + local_dict[update_key] # description: update routing table ใหม่
    round = round + 1 # description: นับรอบการทำงาน
    print_routing_table(node_name,round,output_dict) # description: print routing table
    # print('check distance: ',local_dict)
    if(have_new_data): # Description: มีข้อมูลใหม่
        have_new_data = False
        start_routing(neighbour_addr, node_name, local_dict) # Description: เข้าขั้นตอน ส่ง + ฟัง
    else:
        hello_message(neighbour_addr, node_name) # Description: hello message บอกว่ายังอยู่ใน network
        start_routing(neighbour_addr, node_name, local_dict) # Description: เข้าขั้นตอน ส่ง + ฟัง

# Description: ส่ง routing table ให้เพื่อนบ้าน
def update_news_to_neighbours(addresses, this_node, dv):
    for addr in addresses:
        # Description: client process ส่งข้อมูล ไปให้ neightbor address ด้วย routing table ของตัวเอง
        message = str(this_node) + '->' + str(dv)
        # print('message: ',message)
        localInfo_socket.sendto(message.encode(), addr) 

# Description: hello message บอกว่ายังอยู่ใน network
def hello_message(addresses, this_node):
    for addr in addresses:
        # Description: client process ส่งข้อมูล ไปให้ neightbor address ด้วย hello message ของตัวเอง
        message = this_node+' say HELLO'
        localInfo_socket.sendto(message.encode(), addr) 

# Description: เพิ่ม router ใหม่ที่ไม่มีข้อมูลใน port table และ routing table
def add_router(peer_node,peer_addr,peer_dv):
    global local_dict
    global org_local_dict
    global node_name
    global neighbour_addr
    global output_dict
    global port_table
    # Description: เพิ่มข้อมูลที่ได้มาจาก router ที่ไม่รู้จักให้เป็นเพื่อนบ้าน (debug)
    with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'r') as f: # Description: แก้ไขข้อมูลไว้ debug
        distance_from_neighbor = json.load(f)
    distance_from_neighbor[node_name] = {"distance":peer_dv[node_name], "next_hop":"-"} # Description: update ข้อมูลที่ได้มาจากเพื่อนบ้าน (จากที่อ่านไฟล์ debug มา)
    local_dict[peer_node] = peer_dv[node_name] # Description: update ข้อมูลที่ได้มาจากเพื่อนบ้าน (ลงใน routing table ที่มีการเปลี่ยนแปลงทุกครั้งที่ได้รับข้อมูลจากเพื่อนบ้าน)
    org_local_dict[peer_node] = peer_dv[node_name] # Description: update ข้อมูลที่ได้มาจากเพื่อนบ้าน (ลงใน routing table ดั้งเดิม)
    with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'w+') as new_distance: # Description: เขียนข้อมูลลงไฟล์ debug
        new_distance.write(json.dumps(distance_from_neighbor))
    with open('routing_table/'+node_name +'/'+node_name+ '_distance.json', 'w+') as new_distance_org: # Description: เขียนข้อมูลลงไฟล์ดั้งเดิม
        new_distance_org.write(json.dumps(org_local_dict))
    # add port
    with open('routing_table/'+node_name +'/'+node_name+ '_current_ip.json', 'r') as f: # Description: แก้ไขข้อมูลไว้ debug
        port_from_neighbor = json.load(f)
    port_from_neighbor[peer_node] = {"address":peer_addr, "alive": time.time()} # Description: update เวลา alive
    with open('routing_table/'+node_name +'/'+node_name+ '_current_ip.json', 'w+') as new_port: # Description: เขียนลงไฟล์ debug
        new_port.write(json.dumps(port_from_neighbor))
    neighbour_addr.append(peer_addr) # Description: ให้เก็บไว้ใน array port table
    # Description: add to original json
    with open('routing_table/'+node_name +'/'+node_name+ '_ip.json', 'r') as f_org: # Description: อ่านข้อมูลจากไฟล์ port table ดั้งเดิม
        port_from_neighbor_org = json.load(f_org)
    port_from_neighbor_org[peer_node] = peer_addr # Description: update port table
    with open('routing_table/'+node_name +'/'+node_name+ '_ip.json', 'w+') as new_port_org: # Description: เขียนลงไฟล์ดั้งเดิม
        new_port_org.write(json.dumps(port_from_neighbor_org))
    port_table.update({peer_node:{"address":peer_addr, "alive": time.time()}}) # Description: update เวลา alive (ใช้จริงตอนรัน)
    start_routing(neighbour_addr, node_name, local_dict) # Description: เข้าขั้นตอน ส่ง + ฟัง

# Description: เปลี่ยน link cost
def change_cost_table(source_node,dest_node,new_cost):
    global local_dict # Description: routing table ที่มีการ update อยู่เรื่อย ๆ 
    global org_local_dict # Description: routing table ดั้งเดิม
    # Description: กรณีที่ source กับ dest เป็น router ทั้งคู่ แก้ไขเส้นทางทั้ง 2 ฝั่ง
    if(source_node.find('N')==-1 and dest_node.find('N')==-1):
        # Description: read file source and dest
        with open('routing_table/'+source_node +'/'+source_node+ '_distance.json', 'r') as f:
            new_dict_source = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
        with open('routing_table/'+dest_node +'/'+dest_node+ '_distance.json', 'r') as f:
            new_dict_dest = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
        # Description: set new cost in source and dest.
        new_dict_source[dest_node] = new_cost
        new_dict_dest[source_node] = new_cost
        # Description: write new cost to source and dest. file
        with open('routing_table/'+source_node +'/'+source_node+ '_distance.json', 'w') as new_distance_source:
            new_distance_source.write(json.dumps(new_dict_source))
        with open('routing_table/'+dest_node +'/'+dest_node+ '_distance.json', 'w') as new_distance_dest:
            new_distance_dest.write(json.dumps(new_dict_dest))
    # Description: กรณีที่ source เป็น network กับ dest เป็น router แก้ไขเส้นทางใน routing table router (dest)
    elif(source_node.find('N') != -1):
        # Description: read file dest
        with open('routing_table/'+dest_node +'/'+dest_node+ '_distance.json', 'r') as f:
            new_dict_dest = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
        # Description: set new cost in dest.
        new_dict_dest[source_node] = new_cost
        # Description: write new cost to dest file
        with open('routing_table/'+dest_node +'/'+dest_node+ '_distance.json', 'w') as new_distance_dest:
            new_distance_dest.write(json.dumps(new_dict_dest))
    # Description: กรณีที่ source เป็น router กับ dest เป็น network แก้ไขเส้นทางใน routing table router (source)
    elif(dest_node.find('N') != -1):
        # read file source
        with open('routing_table/'+source_node +'/'+source_node+ '_distance.json', 'r') as f:
            new_dict_source = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
        # set new cost in source.
        new_dict_source[dest_node] = new_cost
        # write new cost to source file
        with open('routing_table/'+source_node +'/'+source_node+ '_distance.json', 'w') as new_distance_source:
            new_distance_source.write(json.dumps(new_dict_source))

# Description: รวมฟังก์ชั่นส่ง + ฟัง
def start_routing(neighbour_addr, node_name, local_dict):
    # print('send data to neighbor --->')
    update_news_to_neighbours(neighbour_addr, node_name, local_dict) # Description: เข้า client process ที่ส่งข้อมูลให้เพื่อนบ้าน
    # Description: เข้า server process เพื่อรับข้อมูลจากที่ส่งให้ใน update_news_to_neighbours
    # print('<-- receive data to neighbor')
    listen_to_news_from_neighbours()

# Description: ล้างข้อมูลที่ใช้ debug routing table
def initial_distance():
    temp_obj = {}
    with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'w+') as output:
        output.write(json.dumps(temp_obj))

# Description: ล้างข้อมูลที่ใช้ debug port table
def initial_ip():
    temp_obj = {}
    with open('routing_table/'+node_name +'/'+node_name+ '_current_ip.json', 'w+') as output:
        output.write(json.dumps(temp_obj))


def main():
    global local_dict
    global org_local_dict
    global node_name
    global neighbour_addr
    global output_dict
    global port_table
    node_name = _argparse().node
    add_node_name = _argparse().add
    delete_node_name = _argparse().delete
    change_cost = _argparse().change


    if(add_node_name != '' or node_name != ''):
        if(add_node_name != ''):
            node_name = add_node_name

        initial_distance()
        initial_ip()

        # get local distance vector information
        with open('routing_table/'+node_name +'/'+node_name+ '_distance.json', 'r') as f:
            local_dict = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict

        with open('routing_table/'+node_name +'/'+node_name+ '_distance.json', 'r') as f:
            org_local_dict = json.load(f) #Description: อ่านไฟล์ distance มาใส่ org_local_dict

        # get ip address information
        with open('routing_table/'+node_name +'/'+node_name+ '_ip.json', 'r') as f:
            ip_dict = json.load(f) # Description: อ่านไฟล์ ip address
        localInfo_socket.bind(tuple(ip_dict[node_name]))  #Description: bind socket to local port

        # get neighbour addresses
        for neighbour in ip_dict.keys():
            address = tuple(ip_dict[neighbour]) # Description: เอา address มาทำเป็น tuple => ()
            if address != tuple(ip_dict[node_name]): # Description: ถ้า address ที่อ่านมาไม่ตรงกับ address ของตัวเอง
                neighbour_addr.append(address) # Description: ให้เก็บไว้ใน array
                port_table.update({neighbour:{"address":address, "alive": time.time()}}) # Description: update port table ที่ใช้เก็บข้อมูลเวลาตอบสนอง
        with open('routing_table/'+node_name +'/'+node_name+ '_current_ip.json', 'w+') as output: # Description: เอาไว้เก็บข้อมูล port table ณ ขณะนั้น (debug)
            output.write(json.dumps(port_table))

        # Initialize the output dict
        for key in local_dict:
            output_dict.update({key: {"distance": local_dict[key], "next_hop": "-"}}) # Description: ทำให้อยู่ใน format ที่จะเอาไว้ส่งต่อได้
        with open('routing_table/'+node_name +'/'+node_name+ '_current_distance.json', 'w+') as output: # Description: เอาไว้เก็บข้อมูล routing table ณ ขณะนั้น (debug)
            output.write(json.dumps(output_dict))
        # Description: ส่ง ข้อมูลให้ neighbor(neighbour_addr) บอกว่ามาจาก node ตัวเอง(node_name) กับข้อมูลระยะห่างของตัวเองกับ neighbor (local_dict)
        start_routing(neighbour_addr, node_name, local_dict) # Description: เริ่มกระบวนการส่งข้อมูล + รับข้อมูล
    else: # Description: กรณีที่มีการเปลี่ยนค่า cost คำสั่ง python main.py --change "source destination new_cost"
        change_list = change_cost.split(' ') # Description: ใช้แยกคำสั่งออกจากกัน [source, destination, new_cost]
        source_node = change_list[0] # Description: เก็บ source
        dest_node = change_list[1] # Description: เก็บ destination
        new_cost = int(change_list[2]) # Description: เก็บค่า cost ใหม่
        change_cost_table(source_node,dest_node,new_cost) # Description: ส่งไปฟังก์ชั่นเพื่อเปลี่ยนค่า cost
        print('Complete!') # Description: สำเร็จการเปลี่ยน cost



if __name__ == '__main__':
    localInfo_socket = socket.socket(AF_INET, SOCK_DGRAM)
    localInfo_socket.settimeout(10)
    main()