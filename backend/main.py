from fastapi import FastAPI
from app.routers import stock
from app.routers import recipes
from app.routers import meals

app = FastAPI(title="KitchenSync API")

app.include_router(stock.router)
app.include_router(recipes.router)
app.include_router(meals.router)

@app.get("/")
def home():
    return {"message": "KitchenSync Backend Running"}