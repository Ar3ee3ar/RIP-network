import time
from pynput.keyboard import Key, Listener, Controller,Events

router = []
neighbor = []
edge = []

listen_keyboard = Controller()

time_out = 5

def on_press(key):
    print('{0} released'.format(key))
    if key == Key.esc:
        # Stop listener
        return False

def create_topology(start,end,cost):
    if(len(end) == len(cost)):
        router.append(start)
        neighbor.append(end)
        edge.append(cost)
##    else:
##        print('make sure amount of end(',len(end),') equal to cost(',len(cost),')')
##        quit()

def remove_router(name):
    index = router.index(name)
    del(router[index])
    del(neighbor[index])
    del(edge[index])
        

create_topology('A',['192.168.1.0/24','192.168.4.0/24','B'],[1,1,1])
##create_topology('B',['A','D','192.168.2.0/24'],[1,1,1])
##create_topology('C',['192.168.2.0/24','192.168.3.0/24','F'],[1,1,1])
create_topology('D',['192.168.4.0/24'],[1])
##create_topology('E',['D','192.168.6.0/24','F'],[1,1,1])
##create_topology('F',['E','C','192.168.5.0/24'],[1,1,1])

while(True):
    time_start = time.time()
    for i in range(len(router)):
        print('At Router ',router[i],', t = 0')
        print('Dest. Subnet | Next hop |Cost')
        print('--------------------------------')
        for j in range(len(neighbor[i])):
            if(neighbor[i][j].find('192') != -1):
                print(neighbor[i][j],'|   -   |',edge[i][j])
        print('--------------------------------\n\n')


    with Events() as events:
        # time.sleep(1)
        event = events.get(5.0)
        print('finish wait')
        # listen_keyboard.press('a')
        # listen_keyboard.release('a')
        if event is None:
            print(time.time())
            pass
        elif event.key == Key.esc:
            command = input('Please enter command :')
            if(command == 'del'):
                name_router = input('please enter router name: ')
                remove_router(name_router)
            if(command == 'break'):
                break
        else:
            pass
    
    # print('out loop event')
    
    new_time = (time.time() - time_start) - time_out
    # print(new_time)
    if(new_time < 0):
        new_time = 0
    time.sleep(new_time)



    
