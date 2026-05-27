import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_current_weather(lat: float, lon: float, unit: str = "celsius") -> dict:
    """Lấy thông tin thời tiết hiện tại của một thành phố.

    Args:
        location: Tên thành phố (ví dụ: "Hanoi", "Ho Chi Minh City").
        unit: Đơn vị nhiệt độ, "celsius" hoặc "fahrenheit". Mặc định "celsius".

    Returns:
        dict chứa thông tin thời tiết: nhiệt độ, mô tả, độ ẩm, tốc độ gió.
    """
    units_param = "metric" if unit == "celsius" else "imperial"
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": units_param,
        "lang": "vi",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            "location": data["name"],
            "temperature": data["main"]["temp"],
            "unit": unit,
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Không thể lấy dữ liệu thời tiết: {str(e)}"}


# Khai báo tool schema 
weather_tool_declaration = {
    "name": "get_current_weather",
    "description": "Lấy thông tin thời tiết hiện tại. BẮT BUỘC sử dụng tọa độ (lat, lon).",
    "parameters": {
        "type": "object",
        "properties": {
            "lat": {
                "type": "number",
                "description": "Vĩ độ (Latitude) lấy từ tool get_coordinates",
            },
            "lon": {
                "type": "number",
                "description": "Kinh độ (Longitude) lấy từ tool get_coordinates",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Đơn vị nhiệt độ.",
            },
        },
        "required": ["lat", "lon"],
    },
}
