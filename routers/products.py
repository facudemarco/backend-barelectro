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
DOMAIN_URL = "mdpuf8ksxirarnlhtl6pxo2xylsjmtq8-barelectro-api.bargiuelectro.com/images"

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

                sub_categorys = conn.execute(
                    text("SELECT sub_category_name FROM sub_categorys WHERE product_id = :id"),
                    {"id": hid}
                ).scalars().all()

                data = dict(product)
                data["main_image"] = main[0] if main else None
                data["images"] = images
                data["details_list"] = details_list
                data["sub_categorys"] = sub_categorys

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
    sub_category: List[str] = Form(None, description="Product sub-category"),
    height: Optional[float] = Form(None, description="Product height (optional)"),
    width: Optional[float] = Form(None, description="Product width (optional)"),
    depth: Optional[float] = Form(None, description="Product depth (optional)"),
    stock: Optional[bool] = Form(None, description="Product stock (optional)"),
    main_image: Optional[UploadFile] = File(default=None, description="Main image"),
    images: Optional[List[UploadFile]] = File(default=None, description="Other images"),
):
    product_id = str(uuid.uuid4())

    try:
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR, exist_ok=True)

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO Products (id, title, price, category, height, width, depth, stock)
                    VALUES (:id, :title, :price, :category, :height, :width, :depth, :stock)
                """),
                {
                    "id": product_id,
                    "title": title,
                    "price": price,
                    "category": category,
                    "height": height,
                    "width": width,
                    "depth": depth,
                    "stock": stock
                }
            )
            # Insert details
            normalized_details = []
            for d in details_items:
                if isinstance(d, str) and "," in d:
                    normalized_details.extend([item.strip() for item in d.split(",") if item.strip()])
                elif d:
                    normalized_details.append(d.strip())

            for d in normalized_details:
                if not d:
                    continue
                conn.execute(
                    text("""
                        INSERT INTO details (id, product_id, detail_text)
                        VALUES (:id, :product_id, :detail_text)
                    """),
                    {"id": str(uuid.uuid4()), "product_id": product_id, "detail_text": d}
                )

            # Insert sub-category
            normalized_subcat = []
            for d in sub_category or []:
                if isinstance(d, str) and "," in d:
                    normalized_subcat.extend([item.strip() for item in d.split(",") if item.strip()])
                elif d:
                    normalized_subcat.append(d.strip())

            for d in normalized_subcat:
                if not d:
                    continue
                conn.execute(
                    text("""
                        INSERT INTO sub_categorys (id, product_id, sub_category_name)
                        VALUES (:id, :product_id, :sub_category_name)
                    """),
                    {"id": str(uuid.uuid4()), "product_id": product_id, "sub_category_name": d}
                )

            # main image
            url_main = None
            if main_image is not None:
                ext = os.path.splitext(main_image.filename or "file.jpg")[1]
                fname = f"{uuid.uuid4()}{ext}"
                path = os.path.join(IMAGES_DIR, fname)
                with open(path, "wb") as buf:
                    shutil.copyfileobj(main_image.file, buf)
                url_main = f"{DOMAIN_URL}/{fname}"
                conn.execute(
                    text("INSERT INTO products_main_imgs (id, product_id, url) VALUES (:id, :product_id, :url)"),
                    {"id": str(uuid.uuid4()), "product_id": product_id, "url": url_main}
                )

            urls_images = []
            if images:
                for img in images:
                    if img is None:
                        continue
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
                "height": height,
                "width": width,
                "depth": depth,
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
    details: List[str] = Form(default=[]),
    category: str = Form(..., description="Product category"),
    width: Optional[float] = Form(None, description="Product width (optional)"),
    height: Optional[float] = Form(None, description="Product height (optional)"),
    depth: Optional[float] = Form(None, description="Product depth (optional)"),
    stock: Optional[bool] = Form(None, description="Product stock (optional)"),
    sub_category: List[str] = Form(None, description="Product sub-category"),
    main_image: Optional[UploadFile] = File(default=None, description="New main image (optional)"),
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
                        category = :category,
                        height = :height,
                        width = :width,
                        depth = :depth,
                        stock = :stock
                    WHERE id = :id
                """),
                {"id": id, "title": title, "price": price, "details": details, "category": category, "height": height, "width": width, "depth": depth, "stock": stock}
            )
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found.")

            # Update details
            result = conn.execute(
                text("UPDATE details SET detail_text = :detail_text WHERE product_id = :id"),
                {"id": id, "detail_text": details}
            )

            # Update sub-category
            result = conn.execute(
                text("UPDATE sub_categorys SET sub_category_name = :sub_category_name WHERE product_id = :id"),
                {"id": id, "sub_category_name": sub_category}
            )

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

                sub_categorys = conn.execute(
                    text("SELECT sub_category_name FROM sub_categorys WHERE product_id = :id"),
                    {"id": product_id}
                ).scalars().all()

                product = dict(row)
                product["main_image"] = main[0] if main else None
                product["images"] = images
                product["details_list"] = details_list
                product["sub_categorys"] = sub_categorys
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

            sub_categorys = conn.execute(
                text("SELECT sub_category_name FROM sub_categorys WHERE product_id = :id"),
                {"id": product_id}
            ).scalars().all()

            product = dict(res)
            product["main_image"] = main[0] if main else None
            product["images"] = images
            product["details_list"] = details_list
            product["sub_categorys"] = sub_categorys

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
                text("DELETE FROM sub_categorys WHERE product_id = :id"),
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
