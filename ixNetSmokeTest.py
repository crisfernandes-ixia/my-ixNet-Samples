""""
smokeTest.py:

    This is a test design to stress the dut during long duration.
    The test will:
        - Connect to an existing REST session
        - Collects information about BGPv4 , OSPFv2 or ISIS-L3 devices ( can be expanded to include other protocols)
        - Collects information about the traffic ( starts if not running )
        - Establishes a steady state picture based on Protocol Summary table ( up sessions ) and Port Stats ( Rx Rate )
        - In a Random loop it will select one of the following actions
          1. Traffic Change: Dynamically modify the rate and packet sizes without over subscribing the port
            - Checks and waits for protocol stability and re-establishes new steady state
          2. Bounce one of the emulations
            - Checks and waits for protocol AND traffic stability
          3. Bounce one of the vports ( Simulate link down / up )
            - Checks and waits for protocol AND traffic stability


Supports IxNetwork API servers:
   - Windows, Windows Connection Mgr and Linux
Requirements:
   - IxNetwork 9.00
   - Python 3+
   - Import the IxNetwork-restpy
   - The combination of Traffic Item Name + Flow Group Name must be unique
Usage:
   Edit file and input:
   Mandatory:
        appServer = 'localhost' # Where the REST session is running from
        restSession = 1         # Session ID for the rest session.
   Optional:
        restPort = None       # In case the REST port is not default 11009
        durationInSec = 300   # How long in seconds to run the test
        periodInSecs = 30.0   # How often execute a random action
        availableActions = ['TrafficChange', 'EmulationBounce','simPortBounce' ]  # Available actions at this time
   Example: python smokeTest.py
"""
################################################################################
# Import the IxNetwork-restpy library
################################################################################
import random
# Requirements
import time
import datetime
from ixnetwork_restpy import *

# Local Class
class steadyState:
    def __init__(self,ixNet):
        """
        Description
        """
        self.ixnet = ixNet
        self.protocolSummarySteadyState = self.CollectStats('Protocols Summary','Protocol Type','Sessions Up')
        self.portSummarySteadyState = self.CollectStats('Port Statistics','Port Name','Rx. Rate (Mbps)')

    def AtSteadyState(self, protocolCheck = True, portStatsCheck = True):
        if protocolCheck:
            protocolCurrState = self.CollectStats('Protocols Summary', 'Protocol Type', 'Sessions Up')
            #check1 = True if [i for i in self.protocolSummarySteadyState if i not in protocolCurrState] == [] else False
            check1 = True
            for protoStat in protocolCurrState:
                pName =  next(iter(protoStat))
                currVal = int(list(protoStat[pName].values())[0])
                currStatsName = str(list(protoStat[pName].keys())[0])
                for orgProtoInfo in self.protocolSummarySteadyState:
                        orgName = next(iter(orgProtoInfo))
                        if orgName == pName:
                            orgVal = int(list(orgProtoInfo[pName].values())[0])
                            if currVal == orgVal:
                                self.ixnet.info('Protocol: ' + pName + ' ' + currStatsName + ' curr value ' + str(currVal) + ' is equal original ' + str(orgVal))
                            else:
                                self.ixnet.info('Protocol: ' + pName + ' ' + currStatsName + ' curr value ' + str(currVal) + ' is NOT equal original ' + str(orgVal))
                                check1 = False
        if portStatsCheck:
            portCurrState = self.CollectStats('Port Statistics', 'Port Name', 'Rx. Rate (Mbps)')
            check2 = True
            for portStat in portCurrState:
                pName =  next(iter(portStat))
                currVal = float(list(portStat[pName].values())[0])
                currStatsName = str(list(portStat[pName].keys())[0])
                for orgPortInfo in self.portSummarySteadyState:
                        orgName = next(iter(orgPortInfo))
                        if orgName == pName:
                            orgVal = float(list(orgPortInfo[pName].values())[0])
                            if currVal == 0 and orgVal == 0:
                                self.ixnet.info('Port: ' + pName + ' ' + currStatsName + ' curr value ' + str(
                                    currVal) + ' is ZERO as original ' + str(orgVal))
                            else:
                                if ((currVal + (currVal * 0.1) >= orgVal or currVal - (currVal * 0.1) <= orgVal) and (currVal > 0)):
                                    self.ixnet.info('Port: ' + pName + ' ' + currStatsName + ' curr value ' + str(currVal) + ' is within 10% of original ' + str(orgVal))
                                else:
                                    self.ixnet.info('Port: ' + pName + ' ' + currStatsName + ' curr value ' + str(currVal) + ' is NOT  within 10% of original ' + str(orgVal))
                                    check2 = False


        if protocolCheck and portStatsCheck:
            return True if check1 and check2 else False
        elif protocolCheck:
            return True if check1 else False
        elif portStatsCheck:
            return True if check2 else False
        else:
            return False

    def WaitForSteadyState(self,timeOut=180,checkInterval=10,checkProtocol=True,checkPortStats=True):
        endTime = time.time() + timeOut
        while True:
            timestamp = time.time()
            value = datetime.datetime.fromtimestamp(timestamp)
            self.ixnet.info('\n')
            self.ixnet.info('Checking steady state: ' + value.strftime('%Y-%m-%d %H:%M:%S'))
            if time.time() > endTime:
                self.ixnet.info('Time is UP !!\n')
                break
            if self.AtSteadyState(checkProtocol,checkPortStats):
                self.ixnet.info('We are at steady state\n')
                break
            else:
                self.ixnet.info('We are NOT at steady state\n')
                time.sleep(checkInterval)


    def CollectStats(self,TabName,columnTitle,columnName):
        protocolsSummary = StatViewAssistant(self.ixnet, TabName)
        sessionType = protocolsSummary.Rows.Columns.index(columnTitle)
        upSessionsIndex = protocolsSummary.Rows.Columns.index(columnName)
        retList = []
        for protoList in protocolsSummary.Rows.RawData:
            tempDic= {}
            tempDic[protoList[sessionType]] = {}
            tempDic[protoList[sessionType]][columnName] = protoList[upSessionsIndex]
            retList.append(tempDic)
        return retList if retList else False

    def RefreshSteadyState(self):
        self.protocolSummarySteadyState = self.CollectStats('Protocols Summary','Protocol Type','Sessions Up')
        self.portSummarySteadyState = self.CollectStats('Port Statistics','Port Name','Rx. Rate (Mbps)')
# Local Class
class emu:
    def __init__(self,ixnet,type,handle):
        """
        Description
        """
        self.type = type
        self.handle = handle
        self.ixnet = ixnet

    def Bounce(self,downTime=10):
        randIndex = random.randrange(len(self.handle.Active.Values))
        newList = []
        for id, x in enumerate(self.handle.Active.Values):
            if id == randIndex:
                newList.append(False)
            else:
                newList.append(True)
        self.handle.Active.ValueList(newList)
        self.ixnet.Globals.Topology.ApplyOnTheFly()
        time.sleep(downTime)
        self.handle.Active.Single(True)
        self.ixnet.Globals.Topology.ApplyOnTheFly()

def bouceVport(ixNetwork,sleepVal=10):
     vporToBounce = random.choice(ixNetwork.Vport.find())
     # In case there are vports in this session that are not mapped
     while True:
         if vporToBounce.ConnectedTo == 'null':
             vporToBounce = random.choice(ixNetwork.Vport.find())
         else:
             break
     ixNetwork.info('Port: ' + vporToBounce.Name + ' selected')
     timestamp = time.time()
     value = datetime.datetime.fromtimestamp(timestamp)
     ixNetwork.info('\n')
     ixNetwork.info('Bringing port down: ' + value.strftime('%Y-%m-%d %H:%M:%S'))
     vporToBounce.LinkUpDn(arg2='down')
     time.sleep(sleepVal)
     value = datetime.datetime.fromtimestamp(time.time())
     ixNetwork.info('\n')
     ixNetwork.info('Bringing port up: ' + value.strftime('%Y-%m-%d %H:%M:%S'))
     vporToBounce.LinkUpDn(arg2='up')

def messAroundWithTraffic(ixNetwork, flowDict, maxPortDict):
    for flowToChange in flowDict:
        maxRate = maxPortDict[flowDict[flowToChange]['txPort']]
        perc = random.randint(a=1, b=maxRate)
        ixNetwork.info('Setting flow item ' + flowToChange + ' to ' + str(
                perc) + '% of line rate -- Source Port: ' + str(flowDict[flowToChange]['txPort']))
        dynTraffObj = flowDict[flowToChange]['handle']
        dynTraffObj.update(RateType='percentLineRate')
        dynTraffObj.update(Rate=perc)
        dynamicFrameSize = flowDict[flowToChange]['dyFrameSizeHandle']
        dynamicFrameSize.update(Type='fixed')
        someRandSize = int(round(random.uniform(128, 1492), 0))
        dynamicFrameSize.update(FixedSize=someRandSize)
        ixNetwork.info('Setting flow item ' + flowToChange + ' to ' + str(
            someRandSize) + ' frame size.')

def main():
    # Local Variables
    appServer = 'localhost'
    restPort = None
    restSession = 1
    durationInSec = 600
    periodInSecs = 60.0
    availableActions = ['TrafficChange', 'EmulationBounce','simPortBounce' ]
    # Log out file
    outLogFile = 'smokeTest_' + time.strftime("%Y%m%d-%H%M%S") + '.log'

    try:
        session = SessionAssistant(IpAddress=appServer, RestPort=restPort, UserName='admin', Password='admin',
                           SessionName=None, SessionId=restSession, ApiKey=None,
                           ClearConfig=False, LogLevel='info', LogFilename=outLogFile)
        ixNetwork = session.Ixnetwork
        ixNetwork.info('Rest Session ' + str(restSession) + ' established.')
        ixNetwork.info('Appserver ' + appServer)
        ixNetwork.info('Test Duration: ' + str(durationInSec) + ' seconds')
        ixNetwork.info('Test Interval: ' + str(periodInSecs) + ' seconds\n')

        # Getting ports
        EmuDevices = []
        topoList = {}

        ixNetwork.info('Grabbing devices')
        for id, topo in enumerate(ixNetwork.Topology.find(), start=1):
            topoList[id] = {}
            topoList[id]['topo'] = topo
            topoList[id]['deviceList'] = topo.DeviceGroup.find()
            for dev in topoList[id]['deviceList'].Ethernet.find().Ipv4.find().BgpIpv4Peer.find():
                if dev.Status == 'started':
                    deviceEmulated = emu(ixNetwork,type='BGP Peer', handle=dev)
                    EmuDevices.append(deviceEmulated)
                    ixNetwork.info('Found BGPv4 device name: ' + dev.Name + ' with ' + str(len(dev.Active.Values)) + ' devices')
            for dev in topoList[id]['deviceList'].Ethernet.find().IsisL3.find():
                if dev.Status == 'started':
                    deviceEmulated = emu(ixNetwork,type='ISIS-L3 RTR', handle=dev)
                    EmuDevices.append(deviceEmulated)
                    ixNetwork.info('Found ISIS-L3 device name: ' + dev.Name + ' with ' + str(len(dev.Active.Values)) + ' devices')
            for dev in topoList[id]['deviceList'].Ethernet.find().Ipv4.find().Ospfv2.find():
                if dev.Status == 'started':
                    deviceEmulated = emu(ixNetwork,type='OSPFv2-RTR', handle=dev)
                    EmuDevices.append(deviceEmulated)
                    ixNetwork.info('Found Ospf device name: ' + dev.Name + ' with ' + str(len(dev.Active.Values)) + ' devices')

        # Get Traffic State
        currentTrafficState = ixNetwork.Traffic.State
        ixNetwork.info('Currently traffic is in ' + currentTrafficState + ' state')
        traffNeedsToStart = False
        if currentTrafficState == 'notRunning' or currentTrafficState == 'stopped' or currentTrafficState == 'unapplied':
            traffNeedsToStart = True

        # Init  Variables
        flowDict = {}
        srcPortDict = {}
        dynamicTraffItems = ixNetwork.Traffic.DynamicRate.find()
        dynamicFramSizes = ixNetwork.Traffic.DynamicFrameSize.find()

        for eachTrafficItem in dynamicTraffItems:
             traffName = eachTrafficItem.TrafficItemName
             if ixNetwork.Traffic.TrafficItem.find(Name=traffName).Enabled:
                 txPort   = eachTrafficItem.TxPort
                 uniqueFlowName = traffName + ':' + eachTrafficItem.HighLevelStreamName
                 flowDict[uniqueFlowName] = {}
                 flowDict[uniqueFlowName]['txPort'] = txPort
                 flowDict[uniqueFlowName]['traffName'] = traffName
                 flowDict[uniqueFlowName]['handle'] = eachTrafficItem
                 if txPort in srcPortDict:
                     srcPortDict[txPort] += 1
                 else:
                     srcPortDict[txPort] = 1

        # Looking into the source traffic ports
        maxPerPort = {}
        for txPort in srcPortDict:
            maxPerPort[txPort] = int(100 / srcPortDict[txPort])

        for TrafficItem in dynamicFramSizes:
            if ixNetwork.Traffic.TrafficItem.find(Name=TrafficItem.TrafficItemName).Enabled:
                uniqueFlowName = TrafficItem.TrafficItemName + ':' + TrafficItem.HighLevelStreamName
                flowDict[uniqueFlowName]['dyFrameSizeHandle'] = TrafficItem

        if traffNeedsToStart:
            ixNetwork.info('Traffic is not running.... starting traffic')
            ixNetwork.Traffic.Apply()
            ixNetwork.Traffic.Start()
            ixNetwork.info("Sleep 30 seconds")
            time.sleep(30)

        stateNow = steadyState(ixNetwork)

        endTime = time.time() + durationInSec
        index = 1
        while True:
            timestamp = time.time()
            value = datetime.datetime.fromtimestamp(timestamp)
            ixNetwork.info('\n')
            ixNetwork.info('Staring Loop ' + str(index) + ' at ' + value.strftime('%Y-%m-%d %H:%M:%S'))
            if time.time() > endTime:
                ixNetwork.info('Time is UP !!\n')
                break
            else:
                ixNetwork.info('Clearing stats and waiting 10 seconds')
                ixNetwork.ClearPortsAndTrafficStats()
                time.sleep(10)
                actionToExecute = random.choice(availableActions)
                ixNetwork.info('Picked at random an action to execute: ' + actionToExecute)
                if actionToExecute == 'EmulationBounce':
                    my_emu = random.choice(EmuDevices)
                    ixNetwork.info('Picked at random an emulation to bounce: ' + str(my_emu.type))
                    my_emu.Bounce()
                    stateNow.WaitForSteadyState()
                elif actionToExecute == 'TrafficChange':
                    ixNetwork.info('Modifying at random traffic rate and pkt length')
                    messAroundWithTraffic(ixNetwork, flowDict, maxPerPort)
                    stateNow.WaitForSteadyState(checkPortStats=False)
                    time.sleep(10)
                    stateNow.RefreshSteadyState()
                elif actionToExecute == 'simPortBounce':
                    bouceVport(ixNetwork)
                    stateNow.WaitForSteadyState()

            ixNetwork.info('End of Loop ' + str(index) + ' sleeping ' + str(periodInSecs) + ' secs\n')
            time.sleep(periodInSecs)

            try:
                flowStatistics = StatViewAssistant(ixNetwork, 'Traffic Item Statistics')
                ixNetwork.info('Loop ' + str(index) + ' - Stats\n')
                ixNetwork.info('{}\n'.format(flowStatistics))
            except:
                continue
            ixNetwork.info('End of loop ' + str(index) + '\n')
            index += 1

        if traffNeedsToStart:
            ixNetwork.info('Traffic was not running.... stopping traffic')
            ixNetwork.Traffic.Stop()
            ixNetwork.info("Sleep 30 seconds")
            time.sleep(30)

    except Exception as errMsg:
        print('\n%s' +  errMsg)

if __name__ == "__main__":
    main()
