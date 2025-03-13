import time
from ixnetwork_restpy import *
import traceback

# 


# Configuration variables
api_server_ip : str = 'localhost'  # IxNetwork API server IP address
outLogFile : str = 'mac_sec_ping_' + time.strftime("%Y%m%d-%H%M%S") + '.log'

# Ping Variables
dest_ip_to_ping : str = '20.20.20.101'
ping_count: int  =10
ping_rate_in_sec: int = 1 
ping_payload_in_bytes : int = 1280

# Connecting to an existing session running on <api_server_ip>  - Example uses Windows ( username and password not needed)
try:
        session = SessionAssistant(IpAddress=api_server_ip,
                                   UserName='cris',
                                   Password='Keysight#12345',
                                   SessionId=1,
                                   ClearConfig=False,
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

# Grab Session Handle
ixnet_session = session.Ixnetwork

# Grabing the First Topology and looking for an IPv4 layer.... 
ipv4_stack = None
deviceGroup_1 = ixnet_session.Topology.find()[0].DeviceGroup.find()[0]

vport = ixnet_session.Topology.find()[0].Ports[0]
vport_name = False
for _thisVport  in ixnet_session.Vport.find():
      if _thisVport.href == vport:
            vport_name = _thisVport.Name

# Check for IPv4 in standard Ethernet stack
try:
    ipv4_stack = deviceGroup_1.Ethernet.find().Ipv4.find()
except Exception as e:
    ixnet_session.info(f"Error finding Ipv4 in Ethernet: {e}")

# If not found, check in StaticMacsec
if not ipv4_stack or not hasattr(ipv4_stack, "index"):
    try:
        ipv4_stack = deviceGroup_1.Ethernet.find().StaticMacsec.find().Ipv4.find()
    except Exception as e:
        ixnet_session.info(f"Error finding Ipv4 in StaticMacsec: {e}")

# Validate if IPv4 was found
if ipv4_stack and hasattr(ipv4_stack, "index") and ipv4_stack.index == 0:
    ixnet_session.info("IP layer found")
else:
    ixnet_session.info("IP layer NOT found -- Quitting")
    exit

ixnet_session.info("Clearing Stats and wating 10 seconds")
ixnet_session.ClearPortsAndTrafficStats()

time.sleep(10)


ixnet_session.info("Sedning ping and waiting 10 seconds after all pings sent.")
ipv4_stack[0].SendPingWithCountAndPayload(dest_ip_to_ping, ping_count, ping_rate_in_sec, ping_payload_in_bytes)
time.sleep(ping_count*ping_rate_in_sec+10)


ixnet_session.info("Looking for Stats in the Global Protocal Stats.")

global_protocol_stats = StatViewAssistant(ixnet_session, 'Global Protocol Statistics')
if vport_name:
    global_protocol_stats.AddRowFilter('Port Name', StatViewAssistant.REGEX, vport_name)
_stat_collected = global_protocol_stats.Rows[0]
pings_sent = int(_stat_collected['Ping Request Tx.'])
pings_received = int(_stat_collected['Ping Reply Rx.'])

if pings_sent == pings_received: 
      ixnet_session.info(f"PASS -- All Pings sent  {pings_sent} were received as expected.")
else:
      ixnet_session.info(f"FAIL -- Pings sent {pings_sent} , pings received {pings_received}")

# Extract the first row of collected stats
_stat_collected = global_protocol_stats.Rows[0]
# Print all statistics using column names
ixnet_session.info("=== Global Protocol Statistics ===\n")
for column_name in global_protocol_stats.ColumnHeaders:
    stat_value = _stat_collected[column_name]
    ixnet_session.info(f"{column_name}: {stat_value}")
