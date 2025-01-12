# Import key functions to make them accessible
from .weather_collector import (
    verify_bucket,
    fetch_weather,
    save_to_s3,
    get_cities,
    main
)