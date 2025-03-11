import time
from ixnetwork_restpy import *
import traceback

# Configuration variables
api_server_ip = 'localhost'  # IxNetwork API server IP address
ix_chassis_ip = '10.80.81.2'  # Ixia chassis IP address
port1 = '2/1'  
capture_control_plane = True
capture_data_plane = False
icmp_request_count = 10  # Number of ICMP request packets to send
src_port_mac = '00:01:CA:FF:EE:01'
# If False the Test Port will try to resolve ; if defined it will NOT ARP for it.
dest_port_mac_list =  False # ['00:11:01:00:00:01']
src_port_ip = "172.16.0.1"
num_src_hosts = 1
port_mask = 24
dst_port_ip = "172.16.1.1"
vlan_id = 100 # Or False if no vlan defined or needed  
pkt_size = 1280

outLogFile : str = 'ping_' + time.strftime("%Y%m%d-%H%M%S") + '.log'

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
        print(f"Session ID not found on the test platform: {my_vars['Global']['rest_session']}")
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
port_map.Connect(ForceOwnership=True)  



topo1 = ixnetwork.Topology.add(Name='Topology 1' + src_port_ip, Ports=vport1)
dev1 = topo1.DeviceGroup.add(Name='Dev Group 1', Multiplier=str(num_src_hosts))
eth1 = dev1.Ethernet.add(Name='ether1')
eth1.Mac.Single(src_port_mac)
if vlan_id:
    eth1.EnableVlans.Single(True)
    eth1.Vlan.find().VlanId.Single(vlan_id)
ip1_traff = eth1.Ipv4.add(Name='Ip ' + src_port_ip)
ip1_traff.Address.Increment(start_value=src_port_ip, step_value="0.0.0.1")
ip1_traff.GatewayIp.Increment(start_value=dst_port_ip, step_value="0.0.0.1")
ip1_traff.Prefix.Single(port_mask)
if dest_port_mac_list:
    ip1_traff.ResolveGateway.Single(value=False)
    ip1_traff.ManualGatewayMac.ValueList(dest_port_mac_list)


ixnetwork.StartAllProtocols(Arg1='sync')
protocolsSummary = StatViewAssistant(ixnetwork, 'Protocols Summary')
protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')
protocolsSummary.CheckCondition('Sessions Down', StatViewAssistant.EQUAL, '0')



# Create a raw traffic item to send ICMP requests
traffic_item = ixnetwork.Traffic.TrafficItem.add(Name='ICMP Traffic', TrafficType='raw', BiDirectional=False, AllowSelfDestined=True)
endpoint_set = traffic_item.EndpointSet.add(Sources=vport1.Protocols.find(), Destinations=vport1.Protocols.find())
config_element = traffic_item.ConfigElement.find()[0]

config_element.FrameRate.Type = 'framesPerSecond'
config_element.FrameRate.Rate = 1
config_element.TransmissionControl.Type = 'fixedFrameCount'
config_element.TransmissionControl.FrameCount = 10
config_element.FrameSize.Type = 'fixed'
config_element.FrameSize.FixedSize = pkt_size


# Uncomment this to show a list of all the available protocol templates (packet headers)
#for protocolHeader in ixnetwork.Traffic.ProtocolTemplate():
#    ixnetwork.info('\n', protocolHeader.DisplayName)
ethernetStackObj = config_element.Stack.find(DisplayName='Ethernet II')
ixnetwork.info('\nConfiguring Ethernet packet header')
ethernetDstField = ethernetStackObj.Field.find(DisplayName='Destination MAC Address')
ethernetDstField.ValueType = "valueList"
if dest_port_mac_list: 
    resolvedMacs = dest_port_mac_list
else: 
    resolvedMacs =  ip1_traff.find().ResolvedGatewayMac 
ethernetDstField.ValueList = resolvedMacs

ethernetSrcField = ethernetStackObj.Field.find(DisplayName='Source MAC Address')
ethernetSrcField.ValueType = 'increment'
ethernetSrcField.StartValue = src_port_mac
ethernetSrcField.StepValue = "00:00:00:00:00:01"
ethernetSrcField.CountValue = num_src_hosts

if vlan_id:
      vlanProtocolTemplate = ixnetwork.Traffic.ProtocolTemplate.find(DisplayName='^VLAN$')
      ethernetStackObj.Append(Arg2=vlanProtocolTemplate)
      vlan_obj = config_element.Stack.find(DisplayName='^VLAN$')
      vlan_id_field_obj = vlan_obj.Field.find(DisplayName='VLAN-ID')
      vlan_id_field_obj.SingleValue = vlan_id

l2Stack = config_element.Stack.find()[1]

 # Add IPv4 packet header after the Ethernet stack
# 1> Get the protocol template for IPv4
ipv4ProtocolTemplate = ixnetwork.Traffic.ProtocolTemplate.find(DisplayName='IPv4')

# 2> Append the IPv4 protocol header after the Ethernet stack.
l2Stack.Append(Arg2=ipv4ProtocolTemplate)

# 3> Get the new IPv4 packet header stack to use it for appending any protocol after IP layer such as 
#    UDP/TCP.
# Look for the IPv4 packet header object.
ipv4StackObj = config_element.Stack.find(DisplayName='IPv4')

# 4> Configure the mpls packet header
ipv4SrcFieldObj = ipv4StackObj.Field.find(DisplayName='Source Address')
ipv4SrcFieldObj.ValueType = 'increment'
ipv4SrcFieldObj.StartValue = src_port_ip
ipv4SrcFieldObj.StepValue = "0.0.0.1"
ipv4SrcFieldObj.CountValue = num_src_hosts

ipv4DstFieldObj = ipv4StackObj.Field.find(DisplayName='Destination Address')
ipv4DstFieldObj.ValueType = 'increment'
ipv4DstFieldObj.StartValue = dst_port_ip
ipv4DstFieldObj.StepValue = "0.0.0.0"

icmpTemplate = ixnetwork.Traffic.ProtocolTemplate.find(DisplayName='ICMP Msg Types: 0,8,13,14,15,16')

ipv4StackObj.Append(Arg2=icmpTemplate)

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
vport1.RxMode = 'captureAndMeasure'
vport1.Capture.SoftwareEnabled = capture_control_plane
vport1.Capture.HardwareEnabled = capture_data_plane
ixnetwork.StartCapture()

# Start traffic
ixnetwork.Traffic.Start()
time.sleep(20)  # Wait for traffic to be transmitted and captured

# Stop traffic and capture
#ixnetwork.Traffic.Stop()
ixnetwork.StopCapture()
icmp_reply_count = 0
# Check if any packets were captured
total_packets = vport1.Capture.ControlPacketCounter
print(f"Total captured packets: {total_packets}")

num_received_icmp_reply = 0

for packetNumber in range(0, total_packets):
        try:
            # Note: GetPacketFromDataCapture() will create the packet header fields
            vport1.Capture.CurrentPacket.GetPacketFromControlCapture(Arg2=packetNumber)
            packetHeaderStacks = vport1.Capture.CurrentPacket.Stack.find()

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
                    if _myTempValue.FieldValue == dst_port_ip:     
                            src_check = True
                elif packetHeader.DisplayName == 'Internet Control Message Protocol':
                    _myType = packetHeader.Field.find(DisplayName = 'Type')
                    if _myType.FieldValue == '0' and src_check:
                        num_received_icmp_reply += 1 
                else:
                    next
                      
print(f"Total ICMP Echo Replies: {num_received_icmp_reply}")


#_myTempValue = packetHeader.Field.find(DisplayName = 'Source')