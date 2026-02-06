from flask import Blueprint, request, jsonify, g
from option_auditor import risk_engine_pro
from webapp.utils import handle_api_error
from webapp.validation import validate_schema
from webapp.schemas import PortfolioAnalysisRequest

safety_bp = Blueprint('safety', __name__, url_prefix='/safety')

@safety_bp.route("/score", methods=["POST"])
@handle_api_error
@validate_schema(PortfolioAnalysisRequest)
def calculate_score():
    data: PortfolioAnalysisRequest = g.validated_data
    result = risk_engine_pro.calculate_retail_safety_score(data.positions)
    return jsonify(result)

@safety_bp.route("/check-allocation", methods=["POST"])
@handle_api_error
@validate_schema(PortfolioAnalysisRequest)
def check_allocation():
    data: PortfolioAnalysisRequest = g.validated_data
    result = risk_engine_pro.check_allocation_concentration(data.positions)
    return jsonify(result)

@safety_bp.route("/what-if", methods=["POST"])
@handle_api_error
@validate_schema(PortfolioAnalysisRequest)
def what_if_scenario():
    data: PortfolioAnalysisRequest = g.validated_data
    # Use default "market_drop_10" as per requirements (FTSE/SPX 10% drop)
    result = risk_engine_pro.calculate_what_if_scenario(data.positions, "market_drop_10")
    return jsonify(result)
