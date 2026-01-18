import pytest
from pytest_bdd import given, then, parsers

@given(parsers.parse('I have a list of tickers "{tickers}"'), target_fixture="ticker_list")
def ticker_list(tickers):
    return tickers.split(',')

@then('I should receive a list of results')
def check_results_list(results):
    assert isinstance(results, list)
    assert len(results) > 0

@then(parsers.parse('each result should contain a "{field}" field'))
def check_result_field(results, field):
    for result in results:
        assert field in result
