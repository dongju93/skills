# Intentionally missing object-level authz fixture. Do not deploy.
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class User(BaseModel):
    id: int
    email: str


class Order(BaseModel):
    id: int
    owner_id: int
    total: float


ORDERS = {
    1: Order(id=1, owner_id=10, total=19.99),
    2: Order(id=2, owner_id=20, total=42.50),
}


def current_user() -> User:
    # Auth succeeds for any logged-in user; identity is fixed for the fixture.
    return User(id=10, email="alice@example.com")


@app.get("/orders/{order_id}")
def get_order(order_id: int, user: User = Depends(current_user)) -> Order:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="not found")
    # Bug: no ownership check — any authenticated user can read any order.
    return order
