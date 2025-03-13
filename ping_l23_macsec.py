import time
from ixnetwork_restpy import *
import traceback

# Configuration variables
api_server_ip = 'localhost'  # IxNetwork API server IP address
ix_chassis_ip = '10.80.81.2'  # Ixia chassis IP address
port1 = '2/7'  
port2 = '2/8'
capture_control_plane = True
capture_data_plane = False
icmp_request_count = 10  # Number of ICMP request packets to send
src_port_mac = '00:0a:CA:FF:EE:01'
dst_port_mac = '00:0a:BA:BE:EE:01'
# If False the Test Port will try to resolve ; if defined it will NOT ARP for it.
dest_port_mac_list =  False # ['00:11:01:00:00:01']
src_port_ip = "172.16.0.1"
num_src_hosts = 1
num_dst_hosts = 1
port_mask = 16
dst_port_ip = "172.16.1.1"
vlan_id = 100 # Or False if no vlan defined or needed  
pkt_size = 1280

outLogFile : str = 'ping_l2l3' + time.strftime("%Y%m%d-%H%M%S") + '.log'

try:
        session = SessionAssistant(IpAddress=api_server_ip,
                                   UserName='cris',
                                   Password='Keysight#12345',
                                   SessionId=1,
                                   ClearConfig=True,
                                   LogLevel='info',
                                   LogFilename=outLogFile)

except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform")
        print(f"Details: {conn_err}")
except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform")
        print(f"Details: {not_found_err}")
except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")
        print(traceback.format_exc())

ixnetwork = session.Ixnetwork


port_map = session.PortMapAssistant()
mySlot, portIndex = port1.split("/")
vport1 = port_map.Map(ix_chassis_ip, mySlot, portIndex, Name="Port1")

mySlot, portIndex = port2.split("/")
vport2 = port_map.Map(ix_chassis_ip, mySlot, portIndex, Name="Port2")

port_map.Connect(ForceOwnership=True)  

# Building From scratch Topology 1 on Port 1
topo1 = ixnetwork.Topology.add(Name='Topology ' + src_port_ip, Ports=vport1)
dev1 = topo1.DeviceGroup.add(Name='Dev Group 1', Multiplier=str(num_src_hosts))
eth1 = dev1.Ethernet.add(Name='ether1')
eth1.Mac.Single(src_port_mac)
if vlan_id:
    eth1.EnableVlans.Single(True)
    eth1.Vlan.find().VlanId.Single(vlan_id)

smacSec = eth1.StaticMacsec.add(Name= 'L2-3 MacSec' + src_port_ip)
smacSec.IncrementingPn = True
smacSec.SourceIp.Increment(start_value=src_port_ip, step_value="0.0.0.1")
smacSec.SendGratArp = False

# Building From scratch Topology 2 on Port 2
topo2 = ixnetwork.Topology.add(Name='Topology ' + dst_port_ip, Ports=vport2)
dev2 = topo2.DeviceGroup.add(Name='Dev Group 2', Multiplier=str(num_dst_hosts))
eth2 = dev2.Ethernet.add(Name='ether2')
eth2.Mac.Single(dst_port_mac)
if vlan_id:
    eth2.EnableVlans.Single(True)
    eth2.Vlan.find().VlanId.Single(vlan_id)
smacSec2 = eth2.StaticMacsec.add(Name= 'L2-3 MacSec ' + dst_port_ip)
smacSec2.IncrementingPn = True
smacSec2.SendGratArp = False
smacSec2.SourceIp.Increment(start_value=dst_port_ip, step_value="0.0.0.1")



ixnetwork.StartAllProtocols(Arg1='sync')
protocolsSummary = StatViewAssistant(ixnetwork, 'Protocols Summary')
protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, 'Static MACSec')
protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
protocolsSummary.CheckCondition('Sessions Down', StatViewAssistant.EQUAL, '0')

# Create a raw traffic item to send ICMP requests
traffic_item = ixnetwork.Traffic.TrafficItem.add(Name='Encrypted ICMP Traffic', TrafficType='ipv4', BiDirectional=False, AllowSelfDestined=True)
endpoint_set = traffic_item.EndpointSet.add(Sources=topo1, Destinations=topo2)

config_element = traffic_item.find(Name='Encrypted ICMP Traffic').ConfigElement.find()[0]

config_element.FrameRate.Type = 'framesPerSecond'
config_element.FrameRate.Rate = 1
config_element.TransmissionControl.Type = 'fixedFrameCount'
config_element.TransmissionControl.FrameCount = 10
config_element.FrameSize.Type = 'fixed'
config_element.FrameSize.FixedSize = pkt_size

ipv4_Stack = config_element.Stack.find(DisplayName='IPv4')
icmpTemplate = ixnetwork.Traffic.ProtocolTemplate.find(DisplayName='ICMP Msg Types: 0,8,13,14,15,16')
ipv4_Stack.AppendProtocol(Arg2=icmpTemplate)

icmpStackObj = config_element.Stack.find(DisplayName='ICMP Msg Types: 0,8,13,14,15,16')
icmpMsgTypeObj = icmpStackObj.Field.find(DisplayName='Message type')
icmpMsgTypeObj.SingleValue = 8
icmpSeqNumberObj = icmpStackObj.Field.find(DisplayName='Sequence number')
icmpSeqNumberObj.ValueType = 'increment'
icmpSeqNumberObj.StartValue = 0
icmpSeqNumberObj.StepValue = 1
icmpSeqNumberObj.CountValue = 10

traffic_item.Generate()
ixnetwork.Traffic.Apply()

# Start capturing control traffic
vport2.RxMode = 'captureAndMeasure'
vport2.Capture.SoftwareEnabled = False
vport2.Capture.HardwareEnabled = True
ixnetwork.StartCapture()

# Start traffic
ixnetwork.Traffic.Start()
time.sleep(20)  # Wait for traffic to be transmitted and captured

# Stop traffic and capture
#ixnetwork.Traffic.Stop()
ixnetwork.StopCapture()
icmp_reply_count = 0
# Check if any packets were captured
total_packets = vport2.Capture.DataCapturedPacketCounter
print(f"Total captured packets: {total_packets}")

num_received_icmp_request = 0

for packetNumber in range(0, total_packets):
        try:
            # Note: GetPacketFromDataCapture() will create the packet header fields
            vport2.Capture.CurrentPacket.GetPacketFromDataCapture(Arg2=packetNumber)
            packetHeaderStacks = vport2.Capture.CurrentPacket.Stack.find()

        except Exception as errMsg:
                print('\nError: {}'.format(errMsg))
                continue

#        for packetHeader in packetHeaderStacks.find():
#                print('\nPacketHeaderName: {}'.format(packetHeader.DisplayName))
#                for field in packetHeader.Field.find():
#                    print('\t{}: {}'.format(field.DisplayName, field.FieldValue)) 

        src_check = False
        for packetHeader in packetHeaderStacks.find():
                #print('\nPacketHeaderName: {}'.format(packetHeader.DisplayName))
                if  packetHeader.DisplayName == 'Internet Protocol':
                    _myTempValue = packetHeader.Field.find(DisplayName = '^Source$')
                    if _myTempValue.FieldValue == src_port_ip:     
                            src_check = True
                elif packetHeader.DisplayName == 'Internet Control Message Protocol':
                    _myType = packetHeader.Field.find(DisplayName = 'Type')
                    if _myType.FieldValue == '8' and src_check:
                        num_received_icmp_request += 1 
                else:
                    next
                      
print(f"Total ICMP Echo Requests: {num_received_icmp_request}")


#_myTempValue = packetHeader.Field.find(DisplayName = 'Source')