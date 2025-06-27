from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

CITY_COORDS = {
    "berlin": (52.52, 13.41),
    "london": (51.5074, -0.1278),
    "newyork": (40.7128, -74.0060),
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "delhi": (28.6139, 77.2090),
    "sydney": (-33.8688, 151.2093),

    "bratislava": (48.1486, 17.1077),
    "kosice": (48.7164, 21.2611),
    "presov": (49.0000, 21.2333),
    "zilina": (49.2231, 18.7408),
    "nitra": (48.3093, 18.0842),
    "trnava": (48.3774, 17.5882),

    "prague": (50.0755, 14.4378),
    "brno": (49.1951, 16.6068),
    "ostrava": (49.8209, 18.2625),
    "plzen": (49.7475, 13.3776),
    "liberec": (50.7671, 15.0562),
    "olomouc": (49.5942, 17.2509),
    "pardubice": (50.0343, 15.7812)
}

favorites = ["bratislava", "brno"]

class CityModel(BaseModel):
    name: str

@app.get("/")
def root():
    return {"message": "Ahoj toto je moj testovaci web na pocasie cez FastAPI na AWS. Pouzivam https://api.open-meteo.com/v1/forecast.  Docs najdes na http://13.60.32.29/docs ..."
                       "zisti pocasie v mieste: /weather/berlin, pocasie v oblubenych miestach: /favourites/weather"
                       "app povoluje CRUD oblubenych miest"}

@app.get("/weather/{city}")
def get_weather(city: str):
    city_key = city.lower()
    if city_key not in CITY_COORDS:
        raise HTTPException(status_code=404, detail="City not supported")

    lat, lon = CITY_COORDS[city_key]
    url = f"https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true"
    }

    response = httpx.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")

    data = response.json().get("current_weather")
    return {
        "city": city.capitalize(),
        "temperature": data["temperature"],
        "windspeed": data["windspeed"],
        "time": data["time"]
    }

@app.post("/favorites", response_model=list[str])
def add_favorite(city: CityModel):
    city_key = city.name.lower()
    if city_key not in CITY_COORDS:
        raise HTTPException(status_code=404, detail="City not supported")

    if city_key in favorites:
        raise HTTPException(status_code=400, detail="City already added")

    favorites.append(city_key)
    return favorites

@app.get("/favorites", response_model=list[str])
def get_favorites():
    return favorites

@app.put("/favorites/{old_city}", response_model=list[str])
def update_favorite(old_city: str, city: CityModel):
    old_city = old_city.lower()
    new_city = city.name.lower()

    if old_city not in favorites:
        raise HTTPException(status_code=404, detail="Old city not in favorites")
    if new_city not in CITY_COORDS:
        raise HTTPException(status_code=404, detail="New city not supported mesta ktore su podporovane: london, berlin, paris, newyork, delhi, bratislava, kosice, praha, brno, trnava...")

    index = favorites.index(old_city)
    favorites[index] = new_city
    return favorites

@app.delete("/favorites/{city}", response_model=list[str])
def delete_favorite(city: str):
    city_key = city.lower()
    if city_key not in favorites:
        raise HTTPException(status_code=404, detail="City not in favorites")
    favorites.remove(city_key)
    return favorites


@app.get("/favorites/weather")
def get_favorites_weather():
    if not favorites:
        return {"message": "No favorite cities added"}

    weather_list = []

    for city_key in favorites:
        lat, lon = CITY_COORDS[city_key]
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true"
        }

        response = httpx.get(url, params=params)
        if response.status_code != 200:
            # Just skip the city if weather fetch fails
            continue

        data = response.json().get("current_weather")
        if not data:
            continue

        weather_list.append({
            "city": city_key.capitalize(),
            "temperature": data["temperature"],
            "windspeed": data["windspeed"],
            "time": data["time"]
        })

    return weather_list
