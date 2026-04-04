from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.user import Users
from models.license import License
from models.cart import CartItem
from schemas.cart import CartItemCreate, CartItemResponse
from utils.deps import get_db, get_current_user

router = APIRouter(tags=["cart"])  


@router.post("/cart/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_item_to_cart(
    cart_item_data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated.")
        license_to_add = db.query(License).filter(License.id == cart_item_data.license_id).first()
        if not license_to_add:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found.")
        existing_item = db.query(CartItem).filter(CartItem.user_id == current_user.id, CartItem.license_id == cart_item_data.license_id).first()
        if existing_item:
            existing_item.quantity = cart_item_data.quantity
            db.commit()
            db.refresh(existing_item)
            return existing_item
        else:
            new_cart_item = CartItem(user_id=current_user.id, license_id=cart_item_data.license_id, quantity=1)
            db.add(new_cart_item)
            db.commit()
            db.refresh(new_cart_item)
            return new_cart_item
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)


@router.get("/cart/items/{user_id}", response_model=List[CartItemResponse])
def get_cart_items(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required")
        cart_items = (
            db.query(CartItem)
            .filter(CartItem.user_id == current_user.id)
            .options(joinedload(CartItem.license).joinedload(License.music))
            .order_by(CartItem.added_at.desc())
            .all()
        )
        return cart_items
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve cart items: {str(e)}")


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(item_id: int, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated.")
        cart_item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == current_user.id).first()
        if not cart_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        db.delete(cart_item)
        db.commit()
        return None
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)


@router.delete("/cart/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated.")
        db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
        db.commit()
        return {"message": "Cart cleared successfully."}
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
