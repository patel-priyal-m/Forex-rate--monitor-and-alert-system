"""
Unit Tests for Utility Functions

Tests core business logic:
- Cross-rate calculation
- Volatility calculation
- Alert checking logic
"""

import pytest
from typing import Tuple
import statistics


# Import functions to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from consumer.rate_processor import calculate_cross_rate
from consumer.alert_engine import check_alert


class TestCrossRateCalculation:
    """Tests for cross-rate calculation logic."""
    
    def test_calculate_cross_rate_basic(self):
        """Test basic cross-rate calculation."""
        # USD/EUR = 0.92, USD/GBP = 0.79
        # EUR/GBP should be 0.79 / 0.92 = 0.8587
        pair_data = ("USD/EUR", 0.92, "USD/GBP", 0.79)
        
        cross_pair, cross_rate = calculate_cross_rate(pair_data)
        
        assert cross_pair == "EUR/GBP"
        assert round(cross_rate, 4) == round(0.79 / 0.92, 4)
    
    def test_calculate_cross_rate_precision(self):
        """Test cross-rate calculation maintains precision."""
        pair_data = ("USD/JPY", 149.50, "USD/EUR", 0.85)
        
        cross_pair, cross_rate = calculate_cross_rate(pair_data)
        
        assert cross_pair == "JPY/EUR"
        # JPY/EUR = 0.85 / 149.50 = 0.005685
        assert abs(cross_rate - 0.005685) < 0.000001
    
    def test_calculate_cross_rate_different_pairs(self):
        """Test cross-rate with different currency pairs."""
        test_cases = [
            (("USD/CAD", 1.35, "USD/AUD", 1.52), "CAD/AUD", 1.52 / 1.35),
            (("USD/CHF", 0.88, "USD/CNY", 7.24), "CHF/CNY", 7.24 / 0.88),
            (("USD/EUR", 0.85, "USD/INR", 83.12), "EUR/INR", 83.12 / 0.85)
        ]
        
        for pair_data, expected_pair, expected_rate in test_cases:
            cross_pair, cross_rate = calculate_cross_rate(pair_data)
            assert cross_pair == expected_pair
            assert round(cross_rate, 4) == round(expected_rate, 4)
    
    def test_calculate_cross_rate_edge_case_one(self):
        """Test cross-rate when one rate is 1.0."""
        pair_data = ("USD/USD", 1.0, "USD/EUR", 0.85)
        
        cross_pair, cross_rate = calculate_cross_rate(pair_data)
        
        assert cross_pair == "USD/EUR"
        assert cross_rate == 0.85
    
    def test_calculate_cross_rate_symmetric(self):
        """Test that cross-rate calculation is symmetric."""
        # EUR/GBP and GBP/EUR should be inverses
        pair_data1 = ("USD/EUR", 0.92, "USD/GBP", 0.79)
        pair_data2 = ("USD/GBP", 0.79, "USD/EUR", 0.92)
        
        _, rate1 = calculate_cross_rate(pair_data1)
        _, rate2 = calculate_cross_rate(pair_data2)
        
        # rate2 should be 1/rate1
        assert abs(rate2 - (1 / rate1)) < 0.000001


class TestAlertChecking:
    """Tests for alert checking logic."""
    
    def test_check_alert_above_triggered(self):
        """Test alert triggers when rate goes above threshold."""
        alert_data = (1, "USD/EUR", "above", 0.80, 0.85)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["alert_id"] == 1
        assert result["pair"] == "USD/EUR"
        assert result["condition"] == "above"
        assert result["threshold"] == 0.80
        assert result["current_rate"] == 0.85
        assert "above" in result["message"].lower()
    
    def test_check_alert_above_not_triggered(self):
        """Test alert doesn't trigger when rate is below threshold."""
        alert_data = (1, "USD/EUR", "above", 0.90, 0.85)
        
        result = check_alert(alert_data)
        
        assert result is None
    
    def test_check_alert_below_triggered(self):
        """Test alert triggers when rate goes below threshold."""
        alert_data = (2, "USD/GBP", "below", 0.75, 0.70)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["alert_id"] == 2
        assert result["pair"] == "USD/GBP"
        assert result["condition"] == "below"
        assert result["threshold"] == 0.75
        assert result["current_rate"] == 0.70
        assert "below" in result["message"].lower()
    
    def test_check_alert_below_not_triggered(self):
        """Test alert doesn't trigger when rate is above threshold."""
        alert_data = (2, "USD/GBP", "below", 0.70, 0.75)
        
        result = check_alert(alert_data)
        
        assert result is None
    
    def test_check_alert_exact_threshold_above(self):
        """Test alert behavior when rate equals threshold (above condition)."""
        alert_data = (3, "USD/JPY", "above", 150.00, 150.00)
        
        result = check_alert(alert_data)
        
        # Rate equals threshold, not greater, so shouldn't trigger
        assert result is None
    
    def test_check_alert_exact_threshold_below(self):
        """Test alert behavior when rate equals threshold (below condition)."""
        alert_data = (4, "USD/CAD", "below", 1.35, 1.35)
        
        result = check_alert(alert_data)
        
        # Rate equals threshold, not less, so shouldn't trigger
        assert result is None
    
    def test_check_alert_large_difference(self):
        """Test alert with large difference between rate and threshold."""
        alert_data = (5, "USD/JPY", "above", 100.00, 150.00)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["current_rate"] == 150.00
        assert result["threshold"] == 100.00
    
    def test_check_alert_small_difference(self):
        """Test alert with very small difference."""
        alert_data = (6, "USD/EUR", "above", 0.85000, 0.85001)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["current_rate"] > result["threshold"]
    
    def test_check_alert_message_format(self):
        """Test that alert message is properly formatted."""
        alert_data = (7, "USD/CHF", "above", 0.90, 0.95)
        
        result = check_alert(alert_data)
        
        assert result is not None
        message = result["message"]
        assert "USD/CHF" in message
        assert "above" in message.lower()
        assert "0.90" in message or "0.9" in message
        assert "0.95" in message


class TestVolatilityCalculation:
    """Tests for volatility calculation logic."""
    
    def test_volatility_with_sufficient_data(self):
        """Test volatility calculation with enough data points."""
        rates = [0.85, 0.86, 0.84, 0.87, 0.85, 0.86]
        
        volatility = statistics.stdev(rates)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    def test_volatility_zero_variance(self):
        """Test volatility with no variance (all same values)."""
        rates = [0.85, 0.85, 0.85, 0.85]
        
        volatility = statistics.stdev(rates)
        
        assert volatility == 0.0
    
    def test_volatility_high_variance(self):
        """Test volatility with high variance."""
        low_variance = [0.85, 0.86, 0.85, 0.86]
        high_variance = [0.80, 0.90, 0.75, 0.95]
        
        vol_low = statistics.stdev(low_variance)
        vol_high = statistics.stdev(high_variance)
        
        assert vol_high > vol_low
    
    def test_volatility_minimum_data_points(self):
        """Test volatility with minimum required data points."""
        rates = [0.85, 0.86]  # Minimum 2 points for stdev
        
        volatility = statistics.stdev(rates)
        
        assert volatility > 0
    
    def test_volatility_insufficient_data(self):
        """Test volatility calculation fails with insufficient data."""
        rates = [0.85]  # Only 1 point
        
        with pytest.raises(statistics.StatisticsError):
            statistics.stdev(rates)


class TestCrossRateEdgeCases:
    """Edge case tests for cross-rate calculations."""
    
    def test_cross_rate_very_small_numbers(self):
        """Test cross-rate with very small rate values."""
        pair_data = ("USD/JPY", 0.0067, "USD/EUR", 0.85)
        
        cross_pair, cross_rate = calculate_cross_rate(pair_data)
        
        assert cross_pair == "JPY/EUR"
        assert cross_rate > 0
        assert cross_rate == 0.85 / 0.0067
    
    def test_cross_rate_very_large_numbers(self):
        """Test cross-rate with very large rate values."""
        pair_data = ("USD/IDR", 15500.0, "USD/EUR", 0.85)
        
        cross_pair, cross_rate = calculate_cross_rate(pair_data)
        
        assert cross_pair == "IDR/EUR"
        assert cross_rate == 0.85 / 15500.0
        assert cross_rate < 0.0001


class TestAlertEdgeCases:
    """Edge case tests for alert checking."""
    
    def test_alert_with_zero_threshold(self):
        """Test alert with zero threshold."""
        alert_data = (1, "USD/EUR", "above", 0.0, 0.85)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["threshold"] == 0.0
    
    def test_alert_with_negative_rate(self):
        """Test alert behavior with negative rate (theoretical)."""
        alert_data = (2, "USD/EUR", "below", 0.0, -0.5)
        
        result = check_alert(alert_data)
        
        assert result is not None
        assert result["current_rate"] == -0.5
    
    def test_alert_with_very_large_threshold(self):
        """Test alert with very large threshold."""
        alert_data = (3, "USD/JPY", "above", 10000.0, 149.50)
        
        result = check_alert(alert_data)
        
        assert result is None  # Rate is below threshold


class TestIntegrationScenarios:
    """Integration tests combining multiple utility functions."""
    
    def test_calculate_multiple_cross_rates(self):
        """Test calculating multiple cross rates in sequence."""
        base_rates = {
            "USD/EUR": 0.85,
            "USD/GBP": 0.73,
            "USD/JPY": 149.50
        }
        
        # Calculate EUR/GBP
        pair_data1 = ("USD/EUR", base_rates["USD/EUR"], "USD/GBP", base_rates["USD/GBP"])
        cross1, rate1 = calculate_cross_rate(pair_data1)
        
        # Calculate EUR/JPY
        pair_data2 = ("USD/EUR", base_rates["USD/EUR"], "USD/JPY", base_rates["USD/JPY"])
        cross2, rate2 = calculate_cross_rate(pair_data2)
        
        assert cross1 == "EUR/GBP"
        assert cross2 == "EUR/JPY"
        assert rate1 > 0
        assert rate2 > 0
    
    def test_alert_sequence_multiple_conditions(self):
        """Test multiple alerts with different conditions."""
        alerts = [
            (1, "USD/EUR", "above", 0.80, 0.85),
            (2, "USD/GBP", "below", 0.75, 0.70),
            (3, "USD/JPY", "above", 150.0, 149.5)
        ]
        
        results = [check_alert(alert) for alert in alerts]
        
        assert results[0] is not None  # Should trigger
        assert results[1] is not None  # Should trigger
        assert results[2] is None       # Should not trigger
