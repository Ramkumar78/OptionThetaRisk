from flask import Blueprint, jsonify
from option_auditor.strategy_metadata import get_strategy_comparison_data

strategy_bp = Blueprint('strategy', __name__)

@strategy_bp.route('/api/strategies/comparison', methods=['GET'])
def get_strategies_comparison():
    """
    Returns the comparison data for all strategies.
    """
    data = get_strategy_comparison_data()
    return jsonify(data)
