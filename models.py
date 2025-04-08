from sqlalchemy import Column, Integer, String, Float, Boolean, Enum
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

class PizzaSize(enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class Pizza(Base):
    __tablename__ = "pizzas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    size = Column(Enum(PizzaSize, create_constraint=True, name="pizzasize"), nullable=False)
    availability = Column(Boolean, default=True)
    outlet_code = Column(String, nullable=True)
