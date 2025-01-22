from ixnetwork_restpy import *

# Case #1 - 
# Session already running - YES
# Enviroment - Windows Application
# Cleaning Config - YES
try:
    session = SessionAssistant(IpAddress='localhost',
                               UserName="",
                               Password="",
                               SessionId=1,
                               ClearConfig=True,
                               LogLevel='info',
                               LogFilename='win_output.txt')

except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform at localserver")
        print(f"Details: {conn_err}")
except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform: id")
        print(f"Details: {not_found_err}")
except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")
    
ixnet_session = session.Ixnetwork

ixnet_session.info(f"My session Id: {session.Session.Id}")


ixnet_session.info(f"Final Step - Clean up - Cleaning up session and leaving it up...bye")
ixnet_session.NewConfig()
ixnet_session = None

# Case #2 - 
# Session already running - No
# Enviroment - Linux
# Cleaning Config - N/A since new session will be created
try:
    session = SessionAssistant(IpAddress='10.80.81.2',
                               UserName="admin",
                               Password="Keysight#12345",
                               SessionId=None,
                               LogLevel='info',
                               LogFilename='linux_output.txt')

except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform at localserver")
        print(f"Details: {conn_err}")
except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform: id")
        print(f"Details: {not_found_err}")
except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")
    
ixnet_session = session.Ixnetwork

ixnet_session.info(f"My session Id: {session.Session.Id}")

ixnet_session.info(f"Final Step - Clean up - Cleaning up session and leaving it up...bye")
session.Session.remove()


# Case #3 - 
# Session already running - No
# Enviroment - Windows ( Connection Manager )
# Cleaning Config - N/A since new session will be created
try:
    session = SessionAssistant(IpAddress='10.80.81.10',
                               UserName="",
                               Password="",
                               SessionId=None,
                               LogLevel='info',
                               LogFilename='connection_manager_output.txt')

except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform at connection manager")
        print(f"Details: {conn_err}")
except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform: id")
        print(f"Details: {not_found_err}")
except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")
    
ixnet_session = session.Ixnetwork

ixnet_session.info(f"My session Id: {session.Session.Id}")

ixnet_session.info(f"Final Step - Clean up - Cleaning up session and leaving it up...bye")
session.Session.remove()


'''
   Args
        ----
        - IpAddress (str): The ip address of the TestPlatform to connect to where test sessions will be created or connected to.
        - RestPort (int): The rest port of the TestPlatform to connect to.
        - UserName (str): The username to be used for authentication
        - Password (str): The password to be used for authentication
        - ApiKey (str): The api key to be used for authentication. If set the ApiKey will override the UserName and Password
        - IgnoreEnvProxy (bool): Ignore the environment proxy bypass settings.
        - VerifyCertificates (bool): Verify the certificate
        - LogFilename (str): The name of the logger log filename.
        - LogLevel (str(LOGLEVEL_NONE|LOGLEVEL_INFO)): The logger log level that will be set.
        - SessionId (int): The id of the session to connect to.
        - SessionName (str): The name of the session to connect to.
        - ApplicationType (str(APP_TYPE_IXNETWORK|APP_TYPE_QUICKTEST)): The type of IxNetwork middleware test session to create
        - ClearConfig (bool): Clear the current configuration
        - UrlPrefix (str): Some appliances (like novus-mini) needs url prefix in their rest url nomenclature
        - IgnoreStrongPasswordPolicy (bool): By default True, it rejects authentication with server if password is weak.
'''