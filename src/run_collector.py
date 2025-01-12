#!/usr/bin/env python3
"""Entry point script for the weather collector.
This script simply imports and runs the main function from the weather_collector package.
"""
import sys
from weather_collector_app.weather_collector import main

if __name__ == "__main__":
    sys.exit(main())