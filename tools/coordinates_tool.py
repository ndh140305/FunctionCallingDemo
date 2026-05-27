import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_coordinates(location: str) -> dict:
    """Chuyển đổi tên địa danh thành tọa độ địa lý (lat, lon)."""
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": location,
        "limit": 1,
        "appid": OPENWEATHER_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return {
                "lat": data[0]["lat"],
                "lon": data[0]["lon"],
                "full_name": f"{data[0].get('name')}, {data[0].get('country')}"
            }
        return {"error": f"Không tìm thấy tọa độ cho địa danh: {location}"}
    except Exception as e:
        return {"error": f"Lỗi Geocoding: {str(e)}"}
    
coords_tool_declaration = {
    "name": "get_coordinates",
    "description": "Tìm tọa độ địa lý (vĩ độ, kinh độ) của một địa danh, tỉnh thành hoặc quốc gia.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Tên địa danh cần tìm tọa độ, ví dụ: 'Lâm Đồng', 'Hà Nội'",
            }
        },
        "required": ["location"],
    },
}