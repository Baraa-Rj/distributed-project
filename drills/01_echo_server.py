import socket

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 5555))
    server_socket.listen()
    print("Server is listening on port 5555...")

    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:  # peer closed the connection
                        print(f"Client {addr} disconnected.")
                        break
                    conn.sendall(data)
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()