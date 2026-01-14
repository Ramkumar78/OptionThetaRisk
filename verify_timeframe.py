from option_auditor.screener import screen_alpha_101, screen_master_convergence, screen_market

try:
    print("Testing Alpha 101 with region='uk' and time_frame='1d'...")
    results_alpha = screen_alpha_101(region='uk', time_frame='1d')
    print(f"Alpha 101 Result Count: {len(results_alpha)}")
except Exception as e:
    print(f"Alpha 101 Failed: {e}")
    raise e

try:
    print("\nTesting Master Convergence with time_frame='1d'...")
    # This call previously would fail if I hadn't updated the signature (or if I passed it to a function that didn't take it)
    results_master = screen_master_convergence(region='us', time_frame='1d')
    print(f"Master Result Count: {len(results_master)}")
except Exception as e:
    print(f"Master Failed: {e}")
    raise e
