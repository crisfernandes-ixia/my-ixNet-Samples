'''

'''

import sys
from ixnetwork_restpy import *
import locale

locale.setlocale(locale.LC_ALL, '')
import time
from helperFunctions import *
import math

TestVars = testVars()
TestVars.chassisIp : str = '10.80.81.12'
TestVars.sessionIp : str= 'localhost'
# Session ID for now is None; meaning we are creating a new session.
TestVars.sessionId : str = 1
TestVars.port1 : str = '1/1'
TestVars.port2 : str = '1/2'
TestVars.cleanConfig : bool = True
TestVars.takePorts : bool = True
TestVars.user : str = 'admin'
TestVars.password : str = 'Keysight#12345'
# Pkt Sizes to test 'min:max:incrBy'
TestVars.pktSize: int = 100
TestVars.numOfQuues: int = 4
TestVars.txClycleTime : str = '1 ms'
TestVars.TransRateInMbps : int = 1_000

'''
Entry    OffSet(us)    Duration(us)    Prios
1           0             300            5
2         300             200            4
3         500             300            5 
4         800             200            6,3
5        1000             300            5 
6        1300             200            0,1,7
7        1500             300            5
8        1800             200            - 

1           0             250            0
2         250             250            1
3         500             250            2
4         750             250            3
-        1000        

'''


def main():

    # description
    outLogFile : str = 'mainqvb_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
    uniqueName : str = 'mainqvb_' + TestVars.user + time.strftime("%Y%m%d-%H%M")
    vport_dic = dict()
    # Creating a list of random MAC addresses to be used during the test.
    luniqueMacs = generate_unique_mac_list(50)
    inScheduler = dict()
    ## The word queue is special and needs to be unique and in ascending order
    
    inScheduler['queue0'] = {'offset' : 0 , 'duration' : 250 , 'priority' : [0]   }
    inScheduler['queue1'] = {'offset' : 250 , 'duration' : 250 , 'priority' : [1] }
    inScheduler['queue2'] = {'offset' : 500 , 'duration' : 250 , 'priority' : [2] }
    inScheduler['queue3'] = {'offset' : 750 , 'duration' : 250 , 'priority' : [3] }
    
    '''
    inScheduler['queue0'] = {'offset' : 0 , 'duration' : 300 , 'priority' : [5]   }
    inScheduler['queue1'] = {'offset' : 300 , 'duration' : 200 , 'priority' : [4] }
    inScheduler['queue2'] = {'offset' : 500 , 'duration' : 300 , 'priority' : [5] }
    inScheduler['queue3'] = {'offset' : 800 , 'duration' : 200 , 'priority' : [6,3] }
    inScheduler['queue4'] = {'offset' : 1000 , 'duration' : 300 , 'priority' : [5]   }
    inScheduler['queue5'] = {'offset' : 1300 , 'duration' : 200 , 'priority' : [0,1,7] }
    inScheduler['queue6'] = {'offset' : 1500 , 'duration' : 300 , 'priority' : [5] }
    inScheduler['queue7'] = {'offset' : 1800 , 'duration' : 200  }
    '''


    try:
        session = SessionAssistant(IpAddress=TestVars.sessionIp,
                                   UserName=TestVars.user,
                                   Password=TestVars.password,
                                   SessionId=TestVars.sessionId,
                                   SessionName=uniqueName,
                                   ClearConfig=TestVars.cleanConfig,
                                   LogLevel='info',
                                   LogFilename=outLogFile)

        ixNet = session.Ixnetwork
        ixNet.Statistics.TimestampPrecision = 9
        ixNet.info(f"Step 1 - Init - Rest Session {session.Session.Id} established.")
        ixNet.info(f"Step 2 - Init - Enable Use Schedule Start Transmit in Test Options -> Global Settings.")
        
        # Calculating the Cycle Time Based on input table
        ixNet.Traffic.UseScheduledStartTransmit = True
        lastQueueKey = 'queue' + str(len(inScheduler) - 1)
        cycleTime =  inScheduler[lastQueueKey]['offset'] + inScheduler[lastQueueKey]['duration']
        ixNet.info(f"Step 3 - Init - Config Cycle Time to {cycleTime} us using as basis {lastQueueKey}.")
        ixNet.Traffic.CycleTimeForScheduledStart = cycleTime
        ixNet.Traffic.CycleTimeUnitForScheduledStart = 'microseconds'

        #nanoSeconds = convert_to_nanoseconds(int(TestVars.txClycleTime.split()[0]),TestVars.txClycleTime.split()[1])
        #qTime = round(nanoSeconds / TestVars.numOfQuues)

        ixNet.info(f"Step 4 - Init - Assign Ports to Session.")
        port_map = session.PortMapAssistant()
        mySlot, portIndex = TestVars.port1.split("/")
        vport_dic["Grand"] =  port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="GrandMaster")
        mySlot, portIndex = TestVars.port2.split("/")
        vport_dic["Slave"] =port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Slave")
        port_map.Connect(ForceOwnership=TestVars.takePorts, IgnoreLinkUp=True)

        ixNet.info(f"Step 5 - Init -  Checking if all ports are up")
        portStats = StatViewAssistant(ixNet, 'Port Statistics')
        boolPortsAreUp = portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up',Timeout=20,RaiseException=False)
        # Setting TX mode to interleaved
        myIndex = 1
        for vport in vport_dic:
            thisPort = ixNet.Vport.find(Name=vport)
            #thisPort.Type = 'novusTenGigLanFcoe'
            portType = thisPort.Type[0].upper() + thisPort.Type[1:]
            ixNet.info(f"Step 5.1 - Init - Setting port {vport} to Interleaved mode")
            thisPort.TxMode = 'interleaved'
            portObj = getattr(thisPort.L1Config, portType)
            #portObj.EnabledFlowControl = False
            if not boolPortsAreUp:
                ixNet.info(f"Step#5.2 - Init - Ports are not up trying to change the media")
                if portObj.Media and portObj.Media == 'fiber':
                    portObj.Media = 'copper'
                elif  portObj.Media and portObj.Media == 'copper':
                    portObj.Media = 'fiber'

        # If ports are not up now we are done.....
        if not boolPortsAreUp:
            ixNet.info(f"Step 5.3 - Init - Checking once more if all ports are up - Abort otherwise")
            portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30,RaiseException=True)

        # GrandMaster 
        ixNet.info(f"Step 6 - Init - Setting up gPTP GrandMaster Side on port {TestVars.port1}")
        topo1 = ixNet.Topology.add(Name='802.1AS Master Topology', Ports=vport_dic["Grand"])
        dev1 = topo1.DeviceGroup.add(Name='GrandMaster - DG', Multiplier='1')
        eth1 = dev1.Ethernet.add(Name='ether')
        eth1.Mac.Single(luniqueMacs.pop())                       
        eth1.EnableVlans.Single(True)
        eth1.Vlan.find().VlanId.Single(100)
        gPtpHandle = eth1.Ptp.add(Name='GM')
        gPtpHandle.Profile.Single('ieee8021as')
        gPtpHandle.Role.Single('master')
        gPtpHandle.StrictGrant.Single(True)

        # Slave
        ixNet.info(f"Step 7 - Init - Setting up gPTP Slave Side on port {TestVars.port2}")
        topo2 = ixNet.Topology.add(Name='802.1AS Slave Topology', Ports=vport_dic["Slave"])
        dev2 = topo2.DeviceGroup.add(Name='Slave - DG', Multiplier='1')
        eth2 = dev2.Ethernet.add(Name='ether')
        eth2.Mac.Single(luniqueMacs.pop())                       
        eth2.EnableVlans.Single(True)
        eth2.Vlan.find().VlanId.Single(100)
        gPtpSHandle = eth2.Ptp.add(Name='Slave')
        gPtpSHandle.Profile.Single('ieee8021as')
     
        ixNet.info(f'Step 8 - Init -  Staring Protocols')
        ixNet.StartAllProtocols(Arg1='sync')
        
        ixNet.info(f'Step 9 - Verify -  PTP sessions are UP')
        protocolsSummary = StatViewAssistant(ixNet, 'Protocols Summary')
        protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^PTP?')
        protocolsSummary.CheckCondition('Sessions Up', StatViewAssistant.EQUAL, 2)
        protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, 0)

        ixNet.info('Step 10 - Init -  Create Unidirectional Raw Traffic Item')
        rawTraffItem = ixNet.Traffic.TrafficItem.add(Name='Raw Traff Item', BiDirectional=False,TrafficType='raw',TrafficItemType='l2L3')
        
        indexNum = 0 
        for _ in range(len(inScheduler)):
            flow = rawTraffItem.EndpointSet.add(Sources= vport_dic["Grand"].Protocols.find() , Destinations=vport_dic["Slave"].Protocols.find())
            flow.Name = "queue" + str(indexNum)
            indexNum += 1

        indexNum = 0 
        initialTime = 0 
        for _ in range(len(inScheduler)):
            configQ1 = rawTraffItem.ConfigElement.find()[indexNum]
            keyName = "queue" + str(indexNum)
            dicVal = inScheduler.get(keyName)
            retVal = getPktsPerDuration(packet_size_in_bytes = TestVars.pktSize, total_time_in_us = dicVal['duration'], transmission_rate_in_Mbps= TestVars.TransRateInMbps)
            ixNet.info(f"According to my calculations using pkt size in bytes of {TestVars.pktSize} and line rate of {TestVars.TransRateInMbps} Mbps")
            ixNet.info(f"Queue {keyName} can send {retVal} pkts during a {dicVal['duration']} us period.")
            # We need to work on this, but let's cap at 1000 so we know this should work
            if retVal > 1000 :  
                configQ1.FrameRate.update(Type='framesPerSecond', Rate=1000)
            else:
                rounded_num = math.floor(retVal / 100) * 100
                ixNet.info(f"Setting frames per second to {rounded_num} to avoid sending more than the window will allow.")
                configQ1.FrameRate.update(Type='framesPerSecond', Rate=rounded_num)

            configQ1.FrameSize.update(Type='fixed', FixedSize = TestVars.pktSize)
            configQ1.TransmissionControl.update(StartDelayUnits = 'microseconds')
            configQ1.TransmissionControl.update(StartDelay = initialTime)
            ethernetStackObj = configQ1.Stack.find(DisplayName='Ethernet II')
            ethernetDstField = ethernetStackObj.Field.find(DisplayName='Destination MAC Address')
            ethernetDstField.ValueType = 'increment'
            ethernetDstField.StartValue = luniqueMacs.pop(0)
            ethernetDstField.StepValue = "00:00:00:00:00:00"
            ethernetDstField.CountValue = 1
            ethernetSrcField = ethernetStackObj.Field.find(DisplayName='Source MAC Address')
            ethernetSrcField.ValueType = 'increment'
            ethernetSrcField.StartValue = luniqueMacs.pop(0)
            ethernetSrcField.StepValue = "00:00:00:00:00:01"
            ethernetSrcField.CountValue = 1
            vlanTemplate = ixNet.Traffic.ProtocolTemplate.find(TemplateName='^vlan-template.xml')
            ethernetStackObj.Append(Arg2=vlanTemplate)
            vlanStackObj = configQ1.Stack.find(DisplayName='VLAN')
            vlanIdPriority = vlanStackObj.Field.find(DisplayName='VLAN Priority')
            if 'priority' in dicVal:
                vlanIdPriority.ValueType = 'valueList'
                vlanIdPriority.ValueList = dicVal['priority']
            vlanIdField = vlanStackObj.Field.find(DisplayName='VLAN-ID')
            vlanIdField.SingleValue = 100
            indexNum += 1
            initialTime += dicVal['duration']

        rawTraffItem.Tracking.find()[0].TrackBy = ["trackingenabled0", "flowGroup0"]
        rawTraffItem.Generate()
        ixNet.Traffic.Apply()
        ixNet.Traffic.Start()  
        time.sleep(30)
        ixNet.Traffic.Stop()  
        
        checkTrafficState(ixNet, state= 'stopped')

        # CHeck #1 -- All Traffic went trough
        traffItemStatistics = StatViewAssistant(ixNet, 'Traffic Item Statistics')
        for flowStat in traffItemStatistics.Rows: 
            if abs(float(flowStat['Rx Frames']) - float(flowStat['Tx Frames'])) < 1 and float(flowStat['Tx Frames']) > 1:
                ixNet.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- PASS")
            else:
                ixNet.info(f"Tx Frames {int(flowStat['Tx Frames']):,} and Rx Frames {int(flowStat['Rx Frames']):,} -- FAILED")
    
        resultsDict = dict()
        flowGrpStatistics = StatViewAssistant(ixNet, 'Flow Statistics')
        for flowStat in flowGrpStatistics.Rows:
             queueId = flowStat['Flow Group']
             resultsDict[queueId] = dict()
             resultsDict[queueId]['First'] = flowStat['Absolute First TimeStamp']
             resultsDict[queueId]['Last'] = flowStat['Absolute Last TimeStamp']
      
        InitVales = dict() 
        firstKey = find_key_with_word(resultsDict, 'queue0')
        InitVales = resultsDict.pop(firstKey)
        _, initFirst = InitVales['First'].split('.')
        _, initLast = InitVales['Last'].split('.')

        for qIndex in range(1,len(resultsDict)+1):
            thisQ = 'queue' + str(qIndex)
            lastQ = 'queue' + str(qIndex - 1)
            valThisQ = find_key_with_word(resultsDict, thisQ) 
            _, firstVal = resultsDict[valThisQ]['First'].split('.')
            _, lastVal  = resultsDict[valThisQ]['Last'].split('.')
            initDelta = float(firstVal) - float(initFirst)
            expectedInitDelta = inScheduler[thisQ]['offset'] - inScheduler[lastQ]['offset']
            expectedInitDelta = convert_to_nanoseconds(expectedInitDelta,'us')
            ixNet.info(f"Comparing Abs First Time stamps between {thisQ} and {lastQ}")
            ixNet.info(f"Expecting {expectedInitDelta} - Got {initDelta} nsec") 
            if compare_numbers(initDelta,expectedInitDelta): 
                ixNet.info(f"Check PASS")
            else:
                ixNet.info(f"Check FAILED")
            initFirst = firstVal

        
    except Exception as errMsg:
        print(f"{errMsg}")

if __name__ == '__main__':
    main()  



    '''
    Sample Run:
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] using python version 3.10.7 (tags/v3.10.7:6cc6b13, Sep  5 2022, 14:08:36) [MSC v.1933 64 bit (AMD64)]
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] using ixnetwork-restpy version 1.1.9
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [WARNING] Verification of certificates is disabled
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] Determining the platform and rest_port using the localhost address...
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [WARNING] Unable to connect to http://localhost:11009.
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] Connection established to `https://localhost:11009 on windows`
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [WARNING] Setting the session name is not supported on the windows platform
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] Using IxNetwork api server version 9.30.2212.7
2023-06-22 15:16:38 [ixnetwork_restpy.connection tid:27228] [INFO] User info IxNetwork/5CD151GQKN/crernand
2023-06-22 15:16:47 [ixnetwork_restpy.connection tid:27228] [INFO] Step 1 - Init - Rest Session 1 established.
2023-06-22 15:16:47 [ixnetwork_restpy.connection tid:27228] [INFO] Step 2 - Init - Enable Use Schedule Start Transmit in Test Options -> Global Settings.
2023-06-22 15:16:47 [ixnetwork_restpy.connection tid:27228] [INFO] Step 3 - Init - Config Cycle Time to 2000 us using as basis queue7.
2023-06-22 15:16:47 [ixnetwork_restpy.connection tid:27228] [INFO] Step 4 - Init - Assign Ports to Session.
2023-06-22 15:16:48 [ixnetwork_restpy.connection tid:27228] [INFO] Adding test port hosts [10.80.81.12]...
2023-06-22 15:16:53 [ixnetwork_restpy.connection tid:27228] [INFO] PortMapAssistant._add_hosts duration: 5.1790242195129395secs
2023-06-22 15:16:53 [ixnetwork_restpy.connection tid:27228] [INFO] Connecting virtual ports to test ports using location
2023-06-22 15:17:10 [ixnetwork_restpy.connection tid:27228] [INFO] PortMapAssistant._connect_ports duration: 17.131136178970337secs
2023-06-22 15:17:10 [ixnetwork_restpy.connection tid:27228] [WARNING] Bypassing link state check
2023-06-22 15:17:10 [ixnetwork_restpy.connection tid:27228] [INFO] Step 5 - Init -  Checking if all ports are up
2023-06-22 15:17:21 [ixnetwork_restpy.connection tid:27228] [INFO] Step 5.1 - Init - Setting port Grand to Interleaved mode
2023-06-22 15:17:21 [ixnetwork_restpy.connection tid:27228] [INFO] Step 5.1 - Init - Setting port Slave to Interleaved mode
2023-06-22 15:17:21 [ixnetwork_restpy.connection tid:27228] [INFO] Step 6 - Init - Setting up gPTP GrandMaster Side on port 1/1
2023-06-22 15:17:22 [ixnetwork_restpy.connection tid:27228] [INFO] Step 7 - Init - Setting up gPTP Slave Side on port 1/2
2023-06-22 15:17:22 [ixnetwork_restpy.connection tid:27228] [INFO] Step 8 - Init -  Staring Protocols
2023-06-22 15:17:28 [ixnetwork_restpy.connection tid:27228] [INFO] Step 9 - Verify -  PTP sessions are UP
2023-06-22 15:17:47 [ixnetwork_restpy.connection tid:27228] [INFO] Step 10 - Init -  Create Unidirectional Raw Traffic Item
2023-06-22 15:23:36 [ixnetwork_restpy.connection tid:27228] [INFO] Currently traffic is in stopped state
2023-06-22 15:24:41 [ixnetwork_restpy.connection tid:27228] [INFO] Tx Frames 164,062 and Rx Frames 164,062 -- PASS
2023-06-22 15:25:44 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue1 and queue0
2023-06-22 15:25:53 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 300000 - Got 300003.0 nsec
2023-06-22 15:26:00 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:26:40 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue2 and queue1
2023-06-22 15:26:43 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 200000 - Got 199995.0 nsec
2023-06-22 15:26:49 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:27:00 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue3 and queue2
2023-06-22 15:27:03 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 300000 - Got 300000.0 nsec
2023-06-22 15:27:06 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:27:14 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue4 and queue3
2023-06-22 15:27:15 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 200000 - Got 200005.0 nsec
2023-06-22 15:27:16 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:27:23 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue5 and queue4
2023-06-22 15:27:24 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 300000 - Got 300000.0 nsec
2023-06-22 15:27:25 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:27:34 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue6 and queue5
2023-06-22 15:27:34 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 200000 - Got 199997.0 nsec
2023-06-22 15:27:37 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS
2023-06-22 15:27:46 [ixnetwork_restpy.connection tid:27228] [INFO] Comparing Abs First Time stamps between queue7 and queue6
2023-06-22 15:27:47 [ixnetwork_restpy.connection tid:27228] [INFO] Expecting 300000 - Got 300000.0 nsec
2023-06-22 15:27:50 [ixnetwork_restpy.connection tid:27228] [INFO] Check PASS

'''
