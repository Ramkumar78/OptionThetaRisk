from functools import wraps
from flask import request, jsonify, g, current_app
from pydantic import ValidationError, BaseModel
from typing import Type, Any, Dict, Union

def validate_schema(schema: Type[BaseModel], source: str = 'json'):
    """
    Decorator to validate request data against a Pydantic model.

    Args:
        schema: The Pydantic model class to validate against.
        source: The source of the data ('json', 'args', 'form').
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data: Union[Dict[str, Any], list] = {}
                if source == 'json':
                    data = request.get_json(silent=True)
                    if data is None:
                         data = {}
                elif source == 'args':
                    data = request.args.to_dict()
                elif source == 'form':
                    data = request.form.to_dict()

                # Create model instance
                if isinstance(data, list):
                     model = schema(data)
                else:
                     model = schema(**data)

                # Store in g for the route to access
                g.validated_data = model
            except ValidationError as e:
                # Format error messages
                errors = []
                for err in e.errors():
                    # simplify location for better readability
                    loc = ".".join(str(l) for l in err["loc"])
                    errors.append({
                        "field": loc,
                        "msg": err["msg"],
                        "type": err["type"]
                    })
                current_app.logger.warning(f"Validation Error in {request.path}: {errors}")
                return jsonify({"error": "Validation Error", "details": errors}), 400
            except Exception as e:
                current_app.logger.error(f"Unexpected Validation Error in {request.path}: {e}")
                return jsonify({"error": "Invalid request", "details": str(e)}), 400

            return f(*args, **kwargs)
        return wrapper
    return decorator
