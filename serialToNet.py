#!/usr/bin/env python
# -*- coding: utf-8 -*

import os
import sys
import time
import socket
import serial
import threading
import ctypes
import serial.tools.list_ports

serverPort=8000
serverIp='119.23.207.3'
configfile='serconfig'
virtualServer='virtualData'

maxsize=2048

class windowsColor():
    def __init__(self):
        '''Windows CMD命令行颜色'''
        ''' 句柄 '''
        self.STD_INPUT_HANDLE = -10
        self.STD_OUTPUT_HANDLE= -11
        self.STD_ERROR_HANDLE = -12

        self.colors = {
                'black':0x00,
                'darkblue':0x01,
                'darkgreen':0x02,
                'darkskyblue':0x03,
                'darkred':0x04,
                'darkpink':0x05,
                'darkyellow':0x06,
                'darkwhite':0x07,
                'darkgray':0x08,
                'blue':0x09,
                'green':0x0a,
                'skyblue':0xb,
                'red':0x0c,
                'pink':0x0d,
                'yellow':0x0e,
                'white':0x0f
            }

        self.std_out_handle = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        self.lock = threading.Lock();

    def set_cmd_color(self, color):
        bool = ctypes.windll.kernel32.SetConsoleTextAttribute(self.std_out_handle, color)
        return bool

    def reset_color(self):
        self.set_cmd_color(self.colors['white'])

    def print_color_text(self,color, text):
        self.lock.acquire(3)
        self.set_cmd_color(self.colors[color])
        sys.stdout.write('%s' % text)
        self.reset_color()
        self.lock.release()

class serialTools():
    def __init__(self,baudrate):
        self.comPort = 0
        self.baudrate = int(baudrate)
        self.portList = list(serial.tools.list_ports.comports())
    def setSerial(self,comPort):
        try:
            self.comPort = int(comPort)
            if (self.comPort + 1> len(self.portList)):
                print("无效的参数:%s\n"%(comPort))
                return -1
            return 0
        except Exception as e:
            print("无效的参数:%s\n"%(comPort))
            pass
        return -1
    
    def showSerial(self):
        for i in range(0, len(self.portList)):
            print("编号: %d-> %s"%(i,self.portList[i]))       
    def open(self, timer=1):
        com = list(self.portList[self.comPort])
        print("打开串口：%s\n"%(com[0]))
        try:
            self.serial = serial.Serial(com[0],self.baudrate,timeout = timer)
            return 0
        except Exception as e:
            print("串口%s 已经打开或者已经被拔出\n"%(com[0]))
            pass
        return -1       
    def write(self,data):
        try:
            return self.serial.write(data)
        except Exception as e:
            print("串口写入失败：\n%s\n"%e)
            pass      
        return -1
    def read(self,length=1):
        try:
            data = self.serial.read(length)
            return data
        except Exception as e:
            print("串口读取失败 \n%s\n"%e)
            pass     
        return -1
    def readWaitForTimeout(self):
        rdata = bytes()      
        while (True):
            c = self.read()
            if c == b'':
                break
            rdata += c
        return rdata
    
    def readline(self):
        try:
            return self.serial.readline()
        except Exception as e:
            print("串口连接失败\n")
            pass     
        return -1
    def close(self):
        self.serial.close()

class netClient():
    def __init__(self,address, port):
        print("服务器配置：%s(%d)\n"%(address,port))
        self.address = address
        self.port = port
        self.connected = False
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.address,self.port))
            print("连接到服务器 %s->%s\n"%(self.sock.getsockname(),self.sock.getpeername()))
            self.connected = True
            return 0
        except Exception as e:
            print("连接服务器失败\n")
            self.connected = False
            pass
        return -1
    def send(self,data):
        if (not self.connected):
            return -1
        try:
            return self.sock.send(data)
        except Exception as e:
            print("网络发送失败:\n%s\n"%e)
            self.connected = False
            pass     
        return -1
    def recv(self, length=1024):
        if (not self.connected):
            return None
        try:
            return self.sock.recv(length)
        except Exception as e:
            print("网络接收失败:\n%s\n"%e)
            self.connected = False
            pass      
        return None   
    def close(self):
        try:
            self.sock.close()
        except Exception as e:
            pass
        self.connected = False

class virtualNet():
    def __init__(self,name,timer):
        self.name = name
        self.time = timer
    def connect(self):
        try:
            self.file = open(self.name,'rb')
            return 0
        except Exception as e:
            print("打开虚拟服务文件失败\n")
            pass
        return -1
    def strip(self,data):
        dataLen = len(data)
        # 去掉末尾换行回车
        while (dataLen > 0):
            if(data[dataLen-1] == 10 or data[dataLen-1] == 13):
                dataLen = dataLen - 1
                if dataLen < 0:
                    return ''
                continue
            break
        return data[0:dataLen]
    def send(self,data):
        return len(data)
    def recv(self,length=1024):
        line =bytes()
        while(True):
            time.sleep(self.time)
            try:
                line = self.file.readline()
            except Exception as e:
                print("virtual recv %s"%e)
                pass

            if(len(line) != 0):
                if(line[0] == 0x23):
                    continue

            line = line.decode()
            line = line.strip()
            line = line.replace(' ','')
            line = line.replace(',','')
            try:
                line = bytes().fromhex(line.replace('0x','').replace('0X',''))
                if(len(line) > 0):
                    break
            except Exception as e:
                print('无效数据%s'%line)
                pass
            
            self.close()
            self.connect()
        return line
    def close(self):
        self.file.close()


def byteToHexTrans(s):
    return "%s" % ''.join(' 0x%.2x' % x for x in s)

def serialLoop(tSerial,client,wincolor):
    while(True):
        try:
            serialRData = tSerial.readWaitForTimeout()
            if len(serialRData) > 0:
                client.send(serialRData)
                wincolor.print_color_text('darkskyblue',"从TBOX读取数据，长度(%d):\n%s\n\n"%(len(serialRData),byteToHexTrans(serialRData)))
        except Exception as e:
            print("serialLoop %s"%e)
            return -1
    
    return 0

def tboxTest(tSerial,client,wincolor):
    serialThread = threading.Thread(target=serialLoop, args=(tSerial,client,wincolor))
    serialThread.start()

    while(True):
        try:
            serverData = client.recv(maxsize)
            if(serverData == None):
                print('正在尝试重连接.....')
                time.sleep(2)
                client.connect()
                continue
            if len(serverData) > 0:
                tSerial.write(serverData)
                wincolor.print_color_text('darkred',"服务器返回数据，长度(%d):\n%s\n\n"%(len(serverData),byteToHexTrans(serverData)))
        except Exception as e:
            print("tboxTest  %s"%e)
            return -1
    return 0

def waitExit():
    print("异常，程序即将退出!!!")
    time.sleep(3)
    sys.exit(0)
    return 0

def parseConfig(file):
    global serverIp
    global serverPort
    global maxsize
    
    while(True):
        line = file.readline()
        line = line.replace('\n', '')
        if(line == ''):
            break
        sline = line.split('=')
        if (sline[0] == "serverip"):
            serverIp = sline[1]
            print("读取服务器地址：%s\n"%sline[1])
        elif (sline[0] == "port"):
            serverPort = int(sline[1])
            print("读取服务器端口：%s\n"%sline[1])
        elif (sline[0] == "maxsize"):
            maxsize = int(sline[1])
            print("读取服务器接收buffer大小：%s\n"%sline[1])

def configInit():
    if(os.path.exists(configfile)):
        try:
            file = open(configfile)
            parseConfig(file)
        except Exception as e:
            print("配置文件异常，请检查\n")
        finally:
            file.close()
    else:
        print("配置文件%s不存在，使用默认配置\n"%configfile)
        
def main():
    client = None
    wincolor = windowsColor()

    configInit()
    if(os.path.exists(virtualServer)):
        client = virtualNet(virtualServer,1)
    else:
        client = netClient(serverIp,serverPort)
    
    if(client.connect() < 0):
        waitExit()
    
    tboxSerial = serialTools(115200)
    tboxSerial.showSerial()
    
    comPort = input("\n请输入调试串口编号:")
    if(tboxSerial.setSerial(comPort) < 0):
        waitExit()
        
    if(tboxSerial.open(0.05) < 0):
        waitExit()

    tboxTest(tboxSerial, client,wincolor)

    tboxSerial.close()
    client.close()
    waitExit()
    
if __name__ == "__main__":
    main();
