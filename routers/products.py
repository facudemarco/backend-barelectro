from typing import Optional, List
from unicodedata import category
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from Database.dbGetConnection import engine
import uuid
import os
import shutil
from models.product import Products, ProductCreate
import json

router = APIRouter()

IMAGES_DIR = "images/"
DOMAIN_URL = "https://api-barelectro.barelectro.com/images"

@router.get('/products')
def get_products():
    try:
        with engine.begin() as conn:
            result = conn.execute(text("SELECT * FROM Products"))
            rows = result.mappings().all()
            if not rows:
                raise HTTPException(status_code=404, detail="No products found.")

            products = []
            for product in rows:
                hid = product["id"]

                main = conn.execute(
                    text("SELECT url FROM products_main_imgs WHERE product_id = :id"),
                    {"id": hid}
                ).fetchone()

                images = conn.execute(
                    text("SELECT url FROM products_imgs WHERE product_id = :id"),
                    {"id": hid}
                ).scalars().all()

                details_list = conn.execute(
                    text("SELECT detail_text FROM details WHERE product_id = :id"),
                    {"id": hid}
                ).scalars().all()

                data = dict(product)
                data["main_image"] = main[0] if main else None
                data["images"] = images
                data["details_list"] = details_list

                products.append(data)

            return products

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/products/{id}')
def get_products_by_id(id: str):
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM Products WHERE id = :id"), {"id": id}
            ).mappings().first()
            if not res:
                raise HTTPException(status_code=404, detail="Product not found.")
            main = conn.execute(
                text("SELECT url FROM products_main_imgs WHERE product_id = :id"), {"id": id}
            ).fetchone()
            images = conn.execute(
                text("SELECT url FROM products_imgs WHERE product_id = :id"), {"id": id}
            ).scalars().all()
            product = dict(res)
            product["main_image"] = main[0] if main else None
            product["images"] = images
            return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/products/create_product", tags=["Products"])
async def create_product(
    title: str = Form(...),
    price: float = Form(...),
    details_items: List[str] = Form(default=[]),      
    category: str = Form(..., description="Product category"),
    sub_category: str = Form(..., description="Product sub-category"),
    main_image: UploadFile = File(..., description="Main image"),
    images: List[UploadFile] = File(default=[], description="Other images"),
):
    product_id = str(uuid.uuid4())

    try:
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR, exist_ok=True)

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO Products (id, title, price, category, sub_category)
                    VALUES (:id, :title, :price, :category, :sub_category)
                """),
                {
                    "id": product_id,
                    "title": title,
                    "price": price,
                    "category": category,
                    "sub_category": sub_category,
                }
            )

            for d in details_items:
                d = (d or "").strip()
                if not d:
                    continue
                conn.execute(
                    text("""
                        INSERT INTO details (product_id, detail_text)
                        VALUES (:product_id, :detail_text)
                    """),
                    {"product_id": product_id, "detail_text": d}
                )

            main_ext = os.path.splitext(main_image.filename or "file.jpg")[1]
            main_fname = f"{uuid.uuid4()}{main_ext}"
            main_path = os.path.join(IMAGES_DIR, main_fname)
            with open(main_path, "wb") as buf:
                shutil.copyfileobj(main_image.file, buf)
            url_main = f"{DOMAIN_URL}/{main_fname}"
            conn.execute(
                text("""
                    INSERT INTO products_main_imgs (id, product_id, url)
                    VALUES (:id, :product_id, :url)
                """),
                {"id": str(uuid.uuid4()), "product_id": product_id, "url": url_main}
            )

            urls_images = []
            for img in images or []:
                ext = os.path.splitext(img.filename or "file.jpg")[1]
                fname = f"{uuid.uuid4()}{ext}"
                path = os.path.join(IMAGES_DIR, fname)
                with open(path, "wb") as buf:
                    shutil.copyfileobj(img.file, buf)
                url = f"{DOMAIN_URL}/{fname}"
                urls_images.append(url)
                conn.execute(
                    text("""
                        INSERT INTO products_imgs (id, product_id, url)
                        VALUES (:id, :product_id, :url)
                    """),
                    {"id": str(uuid.uuid4()), "product_id": product_id, "url": url}
                )

        return {
            "message": "Product created successfully",
            "product": {
                "id": product_id,
                "title": title,
                "price": price,
                "category": category,
                "sub_category": sub_category,
                "details_list": details_items,
                "main_image": url_main,
                "images": urls_images,
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/products/{id}')
async def update_product(
    id: str,
    title: str = Form(...),
    price: float = Form(...),
    details: str = Form(...),
    main_image: UploadFile | None = File(description="New main image (optional)"),
    images: List[UploadFile] = File(default=[], description="Additional images (optional)")
):
    try:
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR, exist_ok=True)

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE Products SET 
                        title = :title,
                        price = :price,
                        details = :details,
                        category = :category,
                        sub_category = :sub_category
                    WHERE id = :id
                """),
                {"id": id, "title": title, "price": price, "details": details}
            )
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found.")

            if main_image:
                ext = os.path.splitext(main_image.filename or "file.jpg")[1]
                fname = f"{uuid.uuid4()}{ext}"
                path = os.path.join(IMAGES_DIR, fname)
                with open(path, "wb") as buf:
                    shutil.copyfileobj(main_image.file, buf)
                url_main = f"{DOMAIN_URL}/{fname}"

                conn.execute(
                    text("""
                        INSERT INTO products_main_imgs (id, product_id, url)
                        VALUES (:uuid, :product_id, :url)
                        ON DUPLICATE KEY UPDATE url = :url
                    """),
                    {"uuid": str(uuid.uuid4()), "product_id": id, "url": url_main}
                )

            for img in images:
                if not hasattr(img, "filename") or img.filename == "":
                    continue

                ext = os.path.splitext(str(img.filename or "file.jpg"))[1]
                filename = f"{uuid.uuid4()}{ext}"
                filepath = os.path.join(IMAGES_DIR, filename)
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(img.file, buffer)
                public_url = f"{DOMAIN_URL}/{filename}"

                conn.execute(
                    text("""
                        INSERT INTO products_imgs (id, product_id, url)
                        VALUES (:id, :product_id, :url)
                    """),
                    {"id": str(uuid.uuid4()), "product_id": id, "url": public_url}
                )

        return {"message": "Product updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.get('/category/{category}')
def get_products_by_category(category: str):
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM Products WHERE category = :category"), {"category": category}
            ).mappings().all()
            if not res:
                raise HTTPException(status_code=404, detail="No products found for this category.")
            products = []
            for row in res:
                product_id = row["id"]
                main = conn.execute(
                    text("SELECT url FROM products_main_imgs WHERE product_id = :id"), {"id": product_id}
                ).fetchone()
                images = conn.execute(
                    text("SELECT url FROM products_imgs WHERE product_id = :id"), {"id": product_id}
                ).scalars().all()
                details_list = conn.execute(
                    text("SELECT detail_text FROM details WHERE product_id = :id"),
                    {"id": product_id}
                ).scalars().all()
                product = dict(row)
                product["main_image"] = main[0] if main else None
                product["images"] = images
                product["details_list"] = details_list
                products.append(product)
            return products

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/category/{category}/{id}')
def getProductByIdInCategory(category: str, id: str):
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("""
                    SELECT * 
                    FROM Products 
                    WHERE category = :category AND id = :id
                """),
                {"category": category, "id": id}
            ).mappings().first()

            if not res:
                raise HTTPException(status_code=404, detail="No product found for this category and id.")

            product_id = res["id"]

            main = conn.execute(
                text("SELECT url FROM products_main_imgs WHERE product_id = :id"),
                {"id": product_id}
            ).fetchone()

            images = conn.execute(
                text("SELECT url FROM products_imgs WHERE product_id = :id"),
                {"id": product_id}
            ).scalars().all()

            details_list = conn.execute(
                text("SELECT detail_text FROM details WHERE product_id = :id"),
                {"id": product_id}
            ).scalars().all()

            product = dict(res)
            product["main_image"] = main[0] if main else None
            product["images"] = images
            product["details_list"] = details_list

            return product

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/products/{id}')
def delete_product(id: str):
    try:
        urls = []
        with engine.connect() as conn:
            urls += conn.execute(
                text("SELECT url FROM products_imgs WHERE product_id = :id"),
                {"id": id}
            ).scalars().all()
            main = conn.execute(
                text("SELECT url FROM products_main_imgs WHERE product_id = :id"),
                {"id": id}
            ).fetchone()
            if main:
                urls.append(main[0])

        for u in urls:
            fn = u.split("/images/")[-1]
            path = os.path.join(IMAGES_DIR, fn)
            if os.path.exists(path):
                os.remove(path)

        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM details WHERE product_id = :id"),
                {"id": id}
            )

            conn.execute(
                text("DELETE FROM products_imgs WHERE product_id = :id"),
                {"id": id}
            )
            conn.execute(
                text("DELETE FROM products_main_imgs WHERE product_id = :id"),
                {"id": id}
            )

            result = conn.execute(
                text("DELETE FROM Products WHERE id = :id"),
                {"id": id}
            )
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found.")

        return {"message": "Product, details and associated images deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
