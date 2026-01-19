from webapp.app import create_app
import pytest

def test_missing_sdk_503():
    app = create_app(testing=True)
    with app.test_client() as client:
        # We expect 503 because tastytrade is uninstalled
        response = client.post('/api/tastytrade/connect')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
        assert response.status_code == 503

if __name__ == "__main__":
    test_missing_sdk_503()
