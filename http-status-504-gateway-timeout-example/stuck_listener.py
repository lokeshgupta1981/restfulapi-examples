"""A TCP port that never completes new connections, like a host whose accept queue is full."""
import socket
import time

listener = socket.socket()
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", 9505))
listener.listen(0)

# Fill the only slot in the accept queue; the program never calls accept().
filler = socket.create_connection(("127.0.0.1", 9505))
print("port 9505: accept queue is full", flush=True)
while True:
    time.sleep (60)
