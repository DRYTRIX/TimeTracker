"""Unit tests for time rounding functionality"""

import pytest
from app.utils.time_rounding import (
    round_time_duration,
    apply_user_rounding,
    format_rounding_interval,
    get_available_rounding_intervals,
    get_available_rounding_methods,
    get_user_rounding_settings
)


class TestRoundTimeDuration:
    """Test the core time rounding function"""
    
    def test_no_rounding_when_interval_is_one(self):
        """Test that rounding_minutes=1 returns exact duration"""
        assert round_time_duration(3720, 1, 'nearest') == 3720
        assert round_time_duration(3722, 1, 'up') == 3722
        assert round_time_duration(3718, 1, 'down') == 3718
    
    def test_round_to_nearest_5_minutes(self):
        """Test rounding to nearest 5 minute interval"""
        # 62 minutes should round to 60 minutes (nearest 5-min interval)
        assert round_time_duration(3720, 5, 'nearest') == 3600
        # 63 minutes should round to 65 minutes
        assert round_time_duration(3780, 5, 'nearest') == 3900
        # 2 minutes should round to 0
        assert round_time_duration(120, 5, 'nearest') == 0
        # 3 minutes should round to 5
        assert round_time_duration(180, 5, 'nearest') == 300
    
    def test_round_to_nearest_15_minutes(self):
        """Test rounding to nearest 15 minute interval"""
        # 62 minutes should round to 60 minutes
        assert round_time_duration(3720, 15, 'nearest') == 3600
        # 68 minutes should round to 75 minutes
        assert round_time_duration(4080, 15, 'nearest') == 4500
        # 7 minutes should round to 0
        assert round_time_duration(420, 15, 'nearest') == 0
        # 8 minutes should round to 15
        assert round_time_duration(480, 15, 'nearest') == 900
    
    def test_round_up(self):
        """Test always rounding up (ceiling)"""
        # 62 minutes with 15-min interval rounds up to 75
        assert round_time_duration(3720, 15, 'up') == 4500
        # 60 minutes with 15-min interval stays 60 (exact match)
        assert round_time_duration(3600, 15, 'up') == 3600
        # 61 minutes with 15-min interval rounds up to 75
        assert round_time_duration(3660, 15, 'up') == 4500
        # 1 minute with 5-min interval rounds up to 5
        assert round_time_duration(60, 5, 'up') == 300
    
    def test_round_down(self):
        """Test always rounding down (floor)"""
        # 62 minutes with 15-min interval rounds down to 60
        assert round_time_duration(3720, 15, 'down') == 3600
        # 74 minutes with 15-min interval rounds down to 60
        assert round_time_duration(4440, 15, 'down') == 3600
        # 75 minutes with 15-min interval stays 75 (exact match)
        assert round_time_duration(4500, 15, 'down') == 4500
    
    def test_round_to_hour(self):
        """Test rounding to 1 hour intervals"""
        # 62 minutes rounds to 60 minutes (nearest hour)
        assert round_time_duration(3720, 60, 'nearest') == 3600
        # 90 minutes rounds to 120 minutes (nearest hour)
        assert round_time_duration(5400, 60, 'nearest') == 7200
        # 89 minutes rounds to 60 minutes (nearest hour)
        assert round_time_duration(5340, 60, 'nearest') == 3600
    
    def test_invalid_rounding_method_defaults_to_nearest(self):
        """Test that invalid rounding method falls back to 'nearest'"""
        result = round_time_duration(3720, 15, 'invalid')
        expected = round_time_duration(3720, 15, 'nearest')
        assert result == expected
    
    def test_zero_duration(self):
        """Test handling of zero duration"""
        assert round_time_duration(0, 15, 'nearest') == 0
        assert round_time_duration(0, 15, 'up') == 0
        assert round_time_duration(0, 15, 'down') == 0
    
    def test_very_small_durations(self):
        """Test rounding of very small durations"""
        # 30 seconds with 5-min rounding
        assert round_time_duration(30, 5, 'nearest') == 0
        assert round_time_duration(30, 5, 'up') == 300  # Rounds up to 5 minutes
        assert round_time_duration(30, 5, 'down') == 0
    
    def test_very_large_durations(self):
        """Test rounding of large durations"""
        # 8 hours 7 minutes (487 minutes) with 15-min rounding
        # 487 / 15 = 32.47 -> rounds to 32 intervals = 480 minutes = 28800 seconds
        assert round_time_duration(29220, 15, 'nearest') == 28800  # 480 minutes (8 hours)
        # 8 hours 8 minutes (488 minutes) with 15-min rounding
        # 488 / 15 = 32.53 -> rounds to 33 intervals = 495 minutes = 29700 seconds
        assert round_time_duration(29280, 15, 'nearest') == 29700  # 495 minutes (8 hours 15 min)


class TestApplyUserRounding:
    """Test applying user-specific rounding preferences"""
    
    def test_with_rounding_disabled(self):
        """Test that rounding is skipped when disabled for user"""
        class MockUser:
            time_rounding_enabled = False
            time_rounding_minutes = 15
            time_rounding_method = 'nearest'
        
        user = MockUser()
        assert apply_user_rounding(3720, user) == 3720
    
    def test_with_rounding_enabled(self):
        """Test that rounding is applied when enabled"""
        class MockUser:
            time_rounding_enabled = True
            time_rounding_minutes = 15
            time_rounding_method = 'nearest'
        
        user = MockUser()
        # 62 minutes should round to 60 with 15-min interval
        assert apply_user_rounding(3720, user) == 3600
    
    def test_different_user_preferences(self):
        """Test that different users can have different rounding settings"""
        class MockUser1:
            time_rounding_enabled = True
            time_rounding_minutes = 5
            time_rounding_method = 'up'
        
        class MockUser2:
            time_rounding_enabled = True
            time_rounding_minutes = 15
            time_rounding_method = 'down'
        
        duration = 3720  # 62 minutes
        
        # User 1: 5-min up -> 65 minutes
        assert apply_user_rounding(duration, MockUser1()) == 3900
        
        # User 2: 15-min down -> 60 minutes
        assert apply_user_rounding(duration, MockUser2()) == 3600
    
    def test_get_user_rounding_settings(self):
        """Test retrieving user rounding settings"""
        class MockUser:
            time_rounding_enabled = True
            time_rounding_minutes = 10
            time_rounding_method = 'up'
        
        settings = get_user_rounding_settings(MockUser())
        assert settings['enabled'] is True
        assert settings['minutes'] == 10
        assert settings['method'] == 'up'
    
    def test_get_user_rounding_settings_with_defaults(self):
        """Test default values when attributes don't exist"""
        class MockUser:
            pass
        
        settings = get_user_rounding_settings(MockUser())
        assert settings['enabled'] is True
        assert settings['minutes'] == 1
        assert settings['method'] == 'nearest'


class TestFormattingFunctions:
    """Test formatting and helper functions"""
    
    def test_format_rounding_interval(self):
        """Test formatting of rounding intervals"""
        assert format_rounding_interval(1) == 'No rounding (exact time)'
        assert format_rounding_interval(5) == '5 minutes'
        assert format_rounding_interval(15) == '15 minutes'
        assert format_rounding_interval(30) == '30 minutes'
        assert format_rounding_interval(60) == '1 hour'
        assert format_rounding_interval(120) == '2 hours'
    
    def test_get_available_rounding_intervals(self):
        """Test getting available rounding intervals"""
        intervals = get_available_rounding_intervals()
        assert len(intervals) == 6
        assert (1, 'No rounding (exact time)') in intervals
        assert (5, '5 minutes') in intervals
        assert (60, '1 hour') in intervals
    
    def test_get_available_rounding_methods(self):
        """Test getting available rounding methods"""
        methods = get_available_rounding_methods()
        assert len(methods) == 3
        
        method_values = [m[0] for m in methods]
        assert 'nearest' in method_values
        assert 'up' in method_values
        assert 'down' in method_values

