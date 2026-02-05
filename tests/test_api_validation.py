import pytest
from flask import Flask, jsonify, g
from webapp.validation import validate_schema
from pydantic import BaseModel, Field, RootModel
from typing import List, Dict

# Mock schemas
class MockSchema(BaseModel):
    name: str = Field(..., min_length=2)
    age: int = Field(..., gt=0)

class MockListSchema(RootModel):
    root: List[Dict[str, int]]

@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/test/json", methods=["POST"])
    @validate_schema(MockSchema, source='json')
    def test_json():
        return jsonify(g.validated_data.model_dump())

    @app.route("/test/args", methods=["GET"])
    @validate_schema(MockSchema, source='args')
    def test_args():
        return jsonify(g.validated_data.model_dump())

    @app.route("/test/list", methods=["POST"])
    @validate_schema(MockListSchema, source='json')
    def test_list():
        return jsonify(g.validated_data.root)

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_json_validation_success(client):
    resp = client.post("/test/json", json={"name": "Alice", "age": 30})
    assert resp.status_code == 200
    assert resp.json["name"] == "Alice"
    assert resp.json["age"] == 30

def test_json_validation_failure(client):
    resp = client.post("/test/json", json={"name": "A", "age": 30}) # name too short
    assert resp.status_code == 400
    assert "Validation Error" in resp.json["error"]
    assert resp.json["details"][0]["field"] == "name"

def test_args_validation(client):
    resp = client.get("/test/args?name=Bob&age=25")
    assert resp.status_code == 200
    assert resp.json["name"] == "Bob"
    assert resp.json["age"] == 25

def test_args_validation_conversion(client):
    # args are strings, Pydantic should coerce
    resp = client.get("/test/args?name=Charlie&age=40")
    assert resp.status_code == 200
    assert resp.json["age"] == 40

def test_list_validation(client):
    resp = client.post("/test/list", json=[{"val": 1}, {"val": 2}])
    assert resp.status_code == 200
    assert len(resp.json) == 2
    assert resp.json[0]["val"] == 1

def test_missing_field(client):
    resp = client.post("/test/json", json={"name": "Alice"}) # Missing age
    assert resp.status_code == 400
    assert "Validation Error" in resp.json["error"]
    assert resp.json["details"][0]["field"] == "age"
