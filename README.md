# BlueTraceProtocol
A project utilising TCP/UDP and the client-server paradigm  to simulate the widley used BlueTraceProtocol which is used in COVID management

Supports the following features: 
- User login and authentication
- Blocking users on subsequent unsuccessful login attempts
- Creation of a temporary ID for users at set frequency (similar to the protocol used in the real BlueTraceProtocol)
- Allows user to upload their contact log (contacts would be uploaded if a user is diagnosed with COVID)
- Sends UDP and TCP beacons across to users that come in "contact" with each other. Beacons share a temporary ID
