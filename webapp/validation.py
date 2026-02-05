from functools import wraps
from flask import request, jsonify, g
from pydantic import ValidationError, BaseModel, RootModel
from typing import Type, Union

def validate_schema(model: Type[Union[BaseModel, RootModel]], source: str = 'json'):
    """
    Decorator to validate request data against a Pydantic model.

    :param model: The Pydantic model class (BaseModel or RootModel).
    :param source: The source of data: 'json', 'args', or 'form'.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = None
                if source == 'json':
                    data = request.get_json(silent=True)
                    if data is None and not isinstance(data, list):
                        data = {}
                elif source == 'args':
                    data = request.args.to_dict()
                elif source == 'form':
                    data = request.form.to_dict()
                else:
                    return jsonify({"error": f"Invalid validation source: {source}"}), 500

                # Validate
                validated = model.model_validate(data)

                # Store validated data in g for easy access
                g.validated_data = validated

                return f(*args, **kwargs)

            except ValidationError as e:
                return jsonify({
                    "error": "Validation Error",
                    "details": e.errors(include_url=False, include_context=False)
                }), 400
            except Exception as e:
                # Catch JSON decode errors or other unexpected issues
                return jsonify({"error": "Invalid Data", "details": str(e)}), 400

        return wrapper
    return decorator
