from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_superuser
from app.db.session import get_db
from app.models import Product
from app.schemas.admin_products import (
    ProductAdminList,
    ProductAdminOut,
    ProductCreate,
    ProductUpdate,
)
from app.services.admin_products import (
    archive_admin_product,
    create_admin_product,
    get_admin_product,
    list_admin_products,
    set_product_status,
    update_admin_product,
)

router = APIRouter(prefix="/v1/admin/products", tags=["admin-products"])


def _out(product: Product) -> ProductAdminOut:
    return ProductAdminOut(
        slug=product.slug,
        name=product.name,
        shortDescription=product.short_description,
        iconUrl=product.icon_url,
        category=product.category,
        tags=product.tags or [],
        featured=product.featured,
        launchUrl=product.launch_url,
        status=product.status,
        defaultPath=product.default_path,
        embedEnabled=product.embed_enabled,
        sortOrder=product.sort_order,
    )


def _handle_value_error(error: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=ProductAdminList)
def admin_list_products(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    return ProductAdminList(items=[_out(product) for product in list_admin_products(db)])


@router.post("", response_model=ProductAdminOut, status_code=status.HTTP_201_CREATED)
def admin_create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    try:
        return _out(create_admin_product(db, user["id"], body))
    except ValueError as error:
        raise _handle_value_error(error) from error


@router.get("/{slug}", response_model=ProductAdminOut)
def admin_get_product(
    slug: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_superuser),
):
    product = get_admin_product(db, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _out(product)


@router.patch("/{slug}", response_model=ProductAdminOut)
def admin_update_product(
    slug: str,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    product = get_admin_product(db, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        return _out(update_admin_product(db, user["id"], product, body))
    except ValueError as error:
        raise _handle_value_error(error) from error


@router.post("/{slug}/publish", response_model=ProductAdminOut)
def admin_publish_product(
    slug: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    return _set_status(db, slug, user["id"], "enabled")


@router.post("/{slug}/archive", response_model=ProductAdminOut)
def admin_archive_product(
    slug: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    product = _get_or_404(db, slug)
    try:
        return _out(archive_admin_product(db, user["id"], product))
    except ValueError as error:
        raise _handle_value_error(error) from error


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product(
    slug: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superuser),
):
    product = _get_or_404(db, slug)
    try:
        archive_admin_product(db, user["id"], product)
    except ValueError as error:
        raise _handle_value_error(error) from error


def _get_or_404(db: Session, slug: str) -> Product:
    product = get_admin_product(db, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _set_status(db: Session, slug: str, actor_id: str, status_value: str) -> ProductAdminOut:
    product = _get_or_404(db, slug)
    try:
        return _out(set_product_status(db, actor_id, product, status_value))
    except ValueError as error:
        raise _handle_value_error(error) from error
