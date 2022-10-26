# -*- coding = utf-8 -*-
# @Time : 2021-01-03 18:30
# @Author : Danny
# @File : u_main.py
# @Software: PyCharm
import argparse
import json
import time
from socket import *

# เวลาใช้ thread เหมือนกับว่ารันโปรแกรมหลายๆ window พร้อมๆกัน 
# global คือ global ของแต่ละ window

local_dict = {} # routing table ของตัวเอง มีการปรับเปลี่ยนไปหลังจากได้รับข้อมูลมาจาก neighbor router
org_local_dict = {}
node_name = ''
neighbour_addr = []
output_dict = {}


def _argparse():
    # print('parsing args...')
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", "-node_name", default='', help="node name")
    arg = parser.parse_args()
    return arg


def listen_to_news_from_neighbours():
    global node_name
    global local_dict
    global org_local_dict
    global neighbour_addr
    global output_dict
    start_time = time.time() #เวลาที่เริ่มต้นรับข้อมูล
    print(node_name + ' starts listening distance vector from peer nodes...')
    while True:
        try:
            peer_info_b, peer_addr = localInfo_socket.recvfrom(10240) # Description: server process รับข้อมูลจากที่ส่งในฟังก์ชั่น update_news_to_neighbours
            if((peer_info_b.decode()).find('HELLO') != -1):
                print(peer_info_b.decode())
            else:
                peer_node = peer_info_b[:1].decode() # Description: รับข้อมูลชื่อ neighbor node (จาก update_news_to_neighbours คือชื่อ node)
                peer_dv = peer_info_b[1:].decode() # Description: รับข้อมูลระยะทางไป neighbor node (จาก update_news_to_neighbours คือ cost)
                # print(node_name + ' recieve information from neighbour: ' + peer_node + ', peer_addr: ' + str(peer_addr))
                # print('peer distance vector is: ' + peer_dv)
                peer_dict = eval(peer_dv) # Description: ทำให้ cost กลับไปเป็นรูปแบบ json อีกครั้ง (ใช้ eval เพราะรูปแบบที่รับเข้ามาไม่ใช่ json แล้วใช้ json.load ไม่ได้)
                print('peer_dict : ',peer_dict,' ---------------- ',local_dict)

                # If there are keys in the neighbour that local dict does not have
                # add them, and update the distance to infinity
                for neighbour_key in peer_dict: # Description: วนใน neighbor node
                    # Description: จากข้อมูลที่ได้รับจาก neighbor node ถ้าเจอ router ที่ไม่ใช่เพื่อนบ้านและไม่ใช่เราเอง ให้ set เป็นค่าสูงสุดไว้ก่อน (เพราะยังไม่รู้ทางไป)
                    if not neighbour_key in local_dict.keys() and neighbour_key != node_name: 
                        local_dict[neighbour_key] = float('inf') # Description: เพิ่ม node ใหม่ไปใน routing table ของตัวเอง
                        # print('inf node: ',neighbour_key)
                print('new local dict of "',node_name,'": ',local_dict)
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
                        peer_dict[key] = float('inf') # Description: เนื่องจากไปไม่ถึงจึงต้อง set ค่าสูงสุดไว้ก่อน

                    # If there find nearer distance through the peer_node, update the next_hop to peer_node
                    # Description: เปรียบเทียบว่าระหว่างระยะทางจากข้อมูลใน routing table ตัวเอง กับ routing จาก เพื่อนบ้าน เส้นทางไหนสั้นกว่ากัน
                    if local_dict[key] > peer_dict[node_name] + peer_dict[key] and peer_node in org_local_dict.keys():
                        local_dict[key] = peer_dict[node_name] + peer_dict[key] #Description: update ระยะทางให้สั้นลงจากเดิม
                        next_hop = peer_node # Description: ต้องผ่าน neighbour ตัวไหนถึงจะไปถึง
                        distance1 = peer_dict[node_name] + peer_dict[key] # Description: เก็บค่า distance ใหม่เอาไว้เช็คว่าจะ output ไหม
                        update_news_to_neighbours(neighbour_addr, node_name, local_dict)

                    # Description: If the distance and next_hop both changed, update the output distance vector
                    if distance != distance1: # Description: check ว่า distance เปลี่ยนแปลงไหม ถ้าเปลี่ยน update ใน dict ที่เป็น format ไว้ output
                        output_dict.update({key: {"distance": local_dict[key], "next_hop": next_hop}}) # Description: function update เอาไว้เพิ่ม/แก้ไขค่าตามkey ใน dict
                    end_time = time.time() # Description: เวลาที่สิ้นสุดการรับข้อมูล
                    # print(node_name + ": " + str(output_dict))
                    # Description: new print format
                    print('At Router ',node_name,', t = 0')
                    print('Dest. Subnet | Next hop |Cost')
                    print('--------------------------------')
                    for key in dict(output_dict).keys():
                    # for j in range(len(neighbor[i])):
                        # if(neighbor[i][j].find('192') != -1):
                        print(key,'           |   ',output_dict[key]['next_hop'],'    |',output_dict[key]['distance'])
                    print('--------------------------------\n\n')

                    # If there are no more updates in the local dict and the result converges, write the final jason file
                    if end_time - start_time > 20: # ถ้าเวลาผ่านไป 20 s แล้วทำการเขยนข้อมูลลงไปใน json
                        with open(node_name + '_output.json', 'w+') as output:
                            output.write(json.dumps(output_dict))
        except:
            time.sleep(1) # sleep ให้นานกว่านี้หน่อย
            # print('no peers are online') # คิด function hello message
            hello_message(neighbour_addr,node_name) # Description: funcriont hello message
            end_time = time.time()
            #
            if end_time - start_time > 20:
                with open(node_name + '_output.json', 'w+') as output:
                    output.write(json.dumps(output_dict))
                print("Time out, program exits.")
                break


def update_news_to_neighbours(addresses, this_node, dv):
    # print('Start sending local information to neighbors...')
    for addr in addresses:
        # Description: client process ส่งข้อมูล ไปให้ neightbor address ด้วย routing table ของตัวเอง
        localInfo_socket.sendto(this_node.encode() + str(dv).encode(), addr) 

# FIXME: เดี๋ยวค่อยทำให้สวยๆ อีกที แต่ตอนนี้ใช้ได้แล้ว มันจะแสดง (ชื่อ router) say HELLO
def hello_message(addresses, this_node):
    for addr in addresses:
        # Description: client process ส่งข้อมูล ไปให้ neightbor address ด้วย hello message ของตัวเอง
        message = this_node+' say HELLO'
        localInfo_socket.sendto(message.encode(), addr) 


# FIXME:
# อาจจะแก้เป็นไฟล์สมบูรณ์เลยไม่ต้องมารวมกันอีก แบบทำสลับกัน
# จากเดิม แยก -> รวม
# เป็น รวม -> แยก 
def main():
    global local_dict
    global org_local_dict
    global node_name
    global neighbour_addr
    global output_dict
    node_name = _argparse().node

    # get local distance vector information
    with open(node_name + '_distance.json', 'r') as f:
        local_dict = json.load(f) #Description: อ่านไฟล์ distance มาใส่ local_dict
    print('local_dict is: ' + str(local_dict))

    with open(node_name + '_distance.json', 'r') as f:
        org_local_dict = json.load(f) #Description: อ่านไฟล์ distance มาใส่ org_local_dict

    # get ip address information
    with open(node_name + '_ip.json', 'r') as f:
        ip_dict = json.load(f) # Description: อ่านไฟล์ ip address
    print('ips of neighbour nodes are: ' + str(ip_dict))
    localInfo_socket.bind(tuple(ip_dict[node_name]))  #Description: bind socket to local port

    # get neighbour addresses
    for neighbour in ip_dict.keys():
        address = tuple(ip_dict[neighbour]) # Description: เอา address มาทำเป็น tuple => ()
        if address != tuple(ip_dict[node_name]): # Description: ถ้า address ที่อ่านมาไม่ตรงกับ address ของตัวเอง
            neighbour_addr.append(address) # Description: ให้เก็บไว้ใน array
    print('neighbour addresses are: ' + str(neighbour_addr))

    # Initialize the output dict
    for key in local_dict:
        output_dict.update({key: {"distance": local_dict[key], "next_hop": key}}) # Description: ทำให้อยู่ใน format ที่จะเอาไว้ส่งต่อได้
    # Description: ส่ง ข้อมูลให้ neighbor(neighbour_addr) บอกว่ามาจาก node ตัวเอง(node_name) กับข้อมูลระยะห่างของตัวเองกับ neighbor (local_dict)
    update_news_to_neighbours(neighbour_addr, node_name, local_dict)
    # Description: เข้า server process เพื่อรับข้อมูลจากที่ส่งให้ใน update_news_to_neighbours
    listen_to_news_from_neighbours()
    # print(output_dict)


if __name__ == '__main__':
    localInfo_socket = socket(AF_INET, SOCK_DGRAM)
    localInfo_socket.settimeout(1)
    main()

