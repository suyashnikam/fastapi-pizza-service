from fastapi import APIRouter, HTTPException, Depends, status, Header
from sqlalchemy.orm import Session
import models, schemas, database
from fastapi_jwt_auth import AuthJWT
import requests
from typing import Optional
from fastapi.encoders import jsonable_encoder
import os
from dotenv import load_dotenv
load_dotenv()
from redis_client import redis_client
import json

pizza_router = APIRouter(prefix="/api/v1/pizza", tags=["pizza"])

# ✅ Create a pizza
@pizza_router.post("/create", response_model=schemas.PizzaResponse, status_code=status.HTTP_201_CREATED)
async def create_pizza(
        pizza: schemas.PizzaCreate,
        db: Session = Depends(database.get_db),
        Authorize: AuthJWT = Depends(),
        Authorization: Optional[str] = Header(None)
):
    try:
        Authorize.jwt_required()
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if role not in ["ADMIN", "STAFF"]:
        raise HTTPException(status_code=403, detail="Only Admin and Staff can create pizzas")

    existing_pizza = db.query(models.Pizza).filter(models.Pizza.name == pizza.name).first()
    if existing_pizza:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pizza already exists")

    if pizza.outlet_code:
        outlet_service_url = os.getenv("OUTLET_SERVICE_BASE_URL", "http://127.0.0.1:8003") + f"/api/v1/outlet/{pizza.outlet_code}"
        try:
            headers = {"Authorization": f"{Authorization}"}
            response = requests.get(outlet_service_url, headers=headers, timeout=5)
            print(response)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Outlet with code '{pizza.outlet_code}' not found")
        except requests.exceptions.RequestException:
            raise HTTPException(status_code=503, detail="Failed to communicate with outlet service")

    new_pizza = models.Pizza(
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=models.PizzaSize[pizza.size.name],
        availability=pizza.availability,
        outlet_code=pizza.outlet_code
    )

    db.add(new_pizza)
    db.commit()
    db.refresh(new_pizza)

    redis_client.delete("all_pizzas")
    if pizza.outlet_code:
        redis_client.delete(f"outlet_pizzas:{pizza.outlet_code}")

    return jsonable_encoder(new_pizza)


# ✅ Get all pizzas
@pizza_router.get("/", response_model=list[schemas.PizzaResponse])
async def get_pizzas(
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None)
):
    cache_key = "all_pizzas"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    pizzas = db.query(models.Pizza).all()
    data = [
        schemas.PizzaResponse(
            id=pizza.id,
            name=pizza.name,
            description=pizza.description,
            price=pizza.price,
            size=pizza.size.value,
            availability=pizza.availability,
            outlet_code=pizza.outlet_code
        ).dict()
        for pizza in pizzas
    ]

    redis_client.set(cache_key, json.dumps(data), ex=300)  # Cache for 5 mins
    return data


# ✅ Get a specific pizza by ID
@pizza_router.get("/{pizza_id}", response_model=schemas.PizzaResponse)
async def get_pizza(
    pizza_id: int,
    db: Session = Depends(database.get_db),
    Authorization: Optional[str] = Header(None)
):
    cache_key = f"pizza:{pizza_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")

    data = schemas.PizzaResponse(
        id=pizza.id,
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=pizza.size.value,
        availability=pizza.availability,
        outlet_code=pizza.outlet_code
    ).dict()

    redis_client.set(cache_key, json.dumps(data), ex=300)
    return data

# ✅ update a specific pizza by ID
@pizza_router.put("/{pizza_id}", response_model=schemas.PizzaResponse)
async def update_pizza(
    pizza_id: int,
    pizza_data: schemas.PizzaUpdate,
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None),
    Authorize: AuthJWT = Depends(),

):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")

    try:
        Authorize.jwt_required()
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if role not in ["ADMIN", "STAFF"]:
        raise HTTPException(status_code=403, detail="Only Admin and Staff can update pizzas")

    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")

    update_data = pizza_data.dict(exclude_unset=True)

    if "size" in update_data:
        update_data["size"] = models.PizzaSize(update_data["size"].upper())

    for key, value in update_data.items():
        setattr(pizza, key, value)

    db.commit()
    db.refresh(pizza)

    # Invalidate cache
    redis_client.delete("all_pizzas")
    redis_client.delete(f"pizza:{pizza_id}")
    if pizza.outlet_code:
        redis_client.delete(f"outlet_pizzas:{pizza.outlet_code}")

    return schemas.PizzaResponse(
        id=pizza.id,
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=pizza.size.value,  # Convert Enum to string
        availability=pizza.availability,
        outlet_code=pizza.outlet_code
    )

# ✅ Delete a specific pizza by ID
@pizza_router.delete("/{pizza_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_pizza(
    pizza_id: int,
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None),
    Authorize: AuthJWT = Depends(),
):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")

    try:
        Authorize.jwt_required()
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if role not in ["ADMIN", "STAFF"]:
        raise HTTPException(status_code=403, detail="Only Admin and Staff can Delete pizzas")

    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")

    db.delete(pizza)
    db.commit()

    # Invalidate cache
    redis_client.delete("all_pizzas")
    redis_client.delete(f"pizza:{pizza_id}")
    if pizza.outlet_code:
        redis_client.delete(f"outlet_pizzas:{pizza.outlet_code}")

    return {"message": f"Pizza with ID {pizza_id} has been deleted successfully"}

# ✅ Get a pizzas for oulet_code
@pizza_router.get("/for-outlet/{outlet_code}", response_model=list[schemas.PizzaResponse])
async def get_pizzas_for_outlet(
    outlet_code: str,
    db: Session = Depends(database.get_db),
    Authorization: Optional[str] = Header(None),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    outlet_service_url = os.getenv("OUTLET_SERVICE_BASE_URL",
                                   "http://127.0.0.1:8003") + f"/api/v1/outlet/{outlet_code}"
    try:
        headers = {"Authorization": Authorization}
        response = requests.get(outlet_service_url, headers=headers, timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Outlet with code '{outlet_code}' not found")
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Failed to communicate with outlet service")

    cache_key = f"outlet_pizzas:{outlet_code}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    pizzas = db.query(models.Pizza).filter(
        (models.Pizza.outlet_code == outlet_code) | (models.Pizza.outlet_code.is_(None))
    ).all()

    data = [
        schemas.PizzaResponse(
            id=pizza.id,
            name=pizza.name,
            description=pizza.description,
            price=pizza.price,
            size=pizza.size.value,
            availability=pizza.availability,
            outlet_code=pizza.outlet_code
        ).dict()
        for pizza in pizzas
    ]

    redis_client.set(cache_key, json.dumps(data), ex=300)
    return data