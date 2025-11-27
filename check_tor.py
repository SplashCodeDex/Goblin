import requests
import socket
import socks

TOR_HOST = "127.0.0.1"
TOR_PORT = 9050 # Default Tor Browser port, or 9050 for system Tor

def check_tor():
    print(f"Checking Tor connection on {TOR_HOST}:{TOR_PORT}...")
    try:
        s = socket.create_connection((TOR_HOST, TOR_PORT), timeout=5)
        s.close()
        print("Socket connection successful.")
    except Exception as e:
        print(f"Socket connection failed: {e}")
        return

    print("Checking IP via Tor...")
    session = requests.session()
    session.proxies = {
        'http':  f'socks5h://{TOR_HOST}:{TOR_PORT}',
        'https': f'socks5h://{TOR_HOST}:{TOR_PORT}'
    }
    try:
        r = session.get("http://httpbin.org/ip", timeout=10)
        print(f"Tor IP: {r.text}")
    except Exception as e:
        print(f"Failed to get IP via Tor: {e}")

if __name__ == "__main__":
    check_tor()
