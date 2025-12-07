import os
import sys
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

def test_startup():
    print("Initializing App...")
    try:
        from webapp.app import create_app
        app = create_app(testing=True)
        print("App initialized.")

        print("Creating Test Client...")
        client = app.test_client()

        print("Requesting / ...")
        resp = client.get("/")
        print(f"Response Code: {resp.status_code}")
        if resp.status_code == 500:
             print("GOT 500 ERROR. Attempting to get traceback won't work easily with client unless propagate_exceptions is set.")
             # Flask test client usually propagates exceptions if testing=True
        else:
             print("Success (or at least not 500).")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    test_startup()
