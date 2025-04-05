from fastapi import APIRouter, HTTPException, Depends, status, Header
from sqlalchemy.orm import Session
import models, schemas, database
import requests
from typing import Optional
from fastapi.encoders import jsonable_encoder

pizza_router = APIRouter(prefix="/pizza", tags=["pizza"])

# # Function to validate token with user-service
# def validate_token(token: str):
#     headers = {"Authorization": f"Bearer {token}"}
#     user_service_url = "http://127.0.0.1:8001/auth/validate"
#
#     try:
#         response = requests.get(user_service_url, headers=headers)
#         response_data = response.json()
#
#         if response.status_code != 200 or not response_data.get("is_valid"):
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
#             )
#
#         return response_data  # This will contain user details like email and username
#
#     except requests.exceptions.RequestException:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="User authentication service unavailable",
#         )


@pizza_router.post("/create", response_model=schemas.PizzaResponse, status_code=status.HTTP_201_CREATED)
async def create_pizza(
        pizza: schemas.PizzaCreate,
        db: Session = Depends(database.get_db),
        Authorization: Optional[str] = Header(None)
):
    # if not authorization:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")
    #
    # # Validate token with user-service
    # user_data = validate_token(authorization.split(" ")[1])

    existing_pizza = db.query(models.Pizza).filter(models.Pizza.name == pizza.name).first()
    if existing_pizza:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pizza already exists")

    # Ensure size is stored as an Enum instance
    new_pizza = models.Pizza(
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=models.PizzaSize[pizza.size.name],  # Convert Pydantic Enum to SQLAlchemy Enum
        availability=pizza.availability
    )

    db.add(new_pizza)
    db.commit()
    db.refresh(new_pizza)

    # Convert the SQLAlchemy model to a JSON-serializable format
    return jsonable_encoder(new_pizza)


# ✅ Get all pizzas (No authentication needed)
@pizza_router.get("/", response_model=list[schemas.PizzaResponse])
async def get_pizzas(
        db: Session = Depends(database.get_db),
        authorization: Optional[str] = Header(None)
):
    pizzas = db.query(models.Pizza).all()

    # Convert enum to string for response
    return [
        schemas.PizzaResponse(
            id=pizza.id,
            name=pizza.name,
            description=pizza.description,
            price=pizza.price,
            size=pizza.size.value,  # Convert Enum to string
            availability=pizza.availability
        )
        for pizza in pizzas
    ]



# ✅ Get a specific pizza by ID (No authentication needed)
@pizza_router.get("/{pizza_id}", response_model=schemas.PizzaResponse)
async def get_pizza(
        pizza_id: int,
        db: Session = Depends(database.get_db),
        authorization: Optional[str] = Header(None)
):
    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")
    return schemas.PizzaResponse(
        id=pizza.id,
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=pizza.size.value,  # Convert Enum to string
        availability=pizza.availability
    )


@pizza_router.put("/{pizza_id}", response_model=schemas.PizzaResponse)
async def update_pizza(
    pizza_id: int,
    pizza_data: schemas.PizzaUpdate,
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")

    # Validate token with user-service
    # user_data = validate_token(authorization.split(" ")[1])

    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")

    update_data = pizza_data.dict(exclude_unset=True)

    # Convert size to uppercase Enum if provided
    if "size" in update_data:
        update_data["size"] = models.PizzaSize(update_data["size"].upper())

    for key, value in update_data.items():
        setattr(pizza, key, value)

    db.commit()
    db.refresh(pizza)

    # Convert SQLAlchemy Enum to string before returning
    return schemas.PizzaResponse(
        id=pizza.id,
        name=pizza.name,
        description=pizza.description,
        price=pizza.price,
        size=pizza.size.value,  # Convert Enum to string
        availability=pizza.availability
    )




@pizza_router.delete("/{pizza_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_pizza(
    pizza_id: int,
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token required")

    # Validate token with user-service
    # user_data = validate_token(authorization.split(" ")[1])

    pizza = db.query(models.Pizza).filter(models.Pizza.id == pizza_id).first()
    if not pizza:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizza not found")

    db.delete(pizza)
    db.commit()

    return {"message": f"Pizza with ID {pizza_id} has been deleted successfully"}

