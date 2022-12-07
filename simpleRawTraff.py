from ixnetwork_restpy import *
import time, random

class testVars: pass
TestVars = testVars()
TestVars.SessionSrvIp = 'localhost:1'
TestVars.User = 'cris'
TestVars.Password = 'Keysight#12345'
TestVars.srcPorts = [ {'location': '10.80.81.12;1;1'}]
TestVars.dstPorts = [ {'location': '10.80.81.12;1;2'}]

def main():
    outLogFile = 'Sample' + time.strftime("%Y%m%d-%H%M%S") + '.log'
    # In case we have a session already established the user will pass <Server IP>:<Session Id>
    # If no session ID is passed in we create a new session and remove at the end of this test.
    sessionIp, sessionId = (TestVars.SessionSrvIp.split(':') + [None])[:2]

    ### IxNetwork - Create or Connect to a Session
    session = SessionAssistant(IpAddress=sessionIp, LogFilename=outLogFile,
                               SessionId=sessionId, ClearConfig=True,
                               UserName=TestVars.User, Password=TestVars.Password, LogLevel='info')

    ix_session = session.Ixnetwork
    ix_session.info('Assign ports')
    portMap = session.PortMapAssistant()
    vport = dict()
    for index, port in enumerate(TestVars.srcPorts,1):
        name = 'src_' + str(index)
        vport[name] = portMap.Map(Location=port['location'], Name = name)
    for index, port in enumerate(TestVars.dstPorts,1):
        name = 'dst_' + str(index)
        vport[name] = portMap.Map(Location=port['location'], Name= name)
    portMap.Connect(ForceOwnership=True)

    for index, srcPort in enumerate(TestVars.srcPorts, 1):
        src_v_port = ix_session.Vport.find(Name='src_' + str(index)).Protocols.find()
        dst_v_port = ix_session.Vport.find(Name='dst_' + str(index)).Protocols.find()
        # Create a Raw Traffic
        traffName = 'SRC_TRAFF_' + str(index)
        raw_traffic_item_obj = ix_session.Traffic.TrafficItem.add(Name='Raw packet', BiDirectional=False, TrafficType='raw')
        raw_traffic_item_obj.EndpointSet.add(Sources=src_v_port, Destinations=dst_v_port)
        raw_traffic_item_obj.update(Name=traffName)
        config_element = raw_traffic_item_obj.ConfigElement.find()[0]
        config_element.FrameRate.update(Type='percentLineRate', Rate=int(1))
        config_element.FrameSize.FixedSize = 1024
        ethernet_stack_obj = ix_session.Traffic.TrafficItem.find(Name=traffName).ConfigElement.find()[0].Stack.find(StackTypeId = 'ethernet$')
        ix_session.info('Configuring Ethernet packet header')
        ethernetDstField = ethernet_stack_obj.Field.find(DisplayName='Destination MAC Address')
        ethernetDstField.ValueType = 'increment'
        ethernetDstField.StartValue = "02:CA:FE:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), 0)
        ethernetDstField.StepValue = "00:00:00:00:00:01"
        ethernetDstField.CountValue = 50
        ethernetSrcField = ethernet_stack_obj.Field.find(DisplayName='Source MAC Address')
        ethernetSrcField.ValueType = 'increment'
        ethernetSrcField.StartValue = "02:BE:FF:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), 0)
        ethernetSrcField.StepValue = "00:00:00:00:00:01"
        ethernetSrcField.CountValue = 50
        raw_traffic_item_obj.Tracking.find()[0].TrackBy = ["trackingenabled0","ethernetIiSourceaddress0"]
        raw_traffic_item_obj.Generate()
        ix_session.Traffic.Apply()
        # Send Prime Traffic
        ix_session.Traffic.Start()
        time.sleep(10)
        ix_session.Traffic.Stop()

        testPass = True

        flowStatistics = StatViewAssistant(ix_session, 'Flow Statistics')
        for flowStat in flowStatistics.Rows:
                ix_session.info(
                    f"{flowStat['Traffic Item']} Src Mac {flowStat['Ethernet II:Source MAC Address']} \
                               Tx Frames: {flowStat['Tx Frames']}  Rx Frames {flowStat['Rx Frames']} ")
                if int(flowStat['Tx Frames']) > 0 and int(flowStat['Frames Delta']) > 0:
                    testPass = False

        if testPass:
            ix_session.info("TEST PASS !!!!!!!!! - NO PACKETS LOST")
        else:
            ix_session.info("TEST FAILED !!!!!!!!! - PACKETS LOST DETECTED")


if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
