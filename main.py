from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers import contact as contact_router
from routers import products as products_router

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://www.barelectro.com",
    "https://barelectro-website.vercel.app",
    "https://barelectro.com",
    "barelectro-website.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
def read_root():
    return {"message": "BarElectro API by iWeb Techonology. All rights reserved"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
app.include_router(contact_router.router, prefix="/contact", tags=["Contact"])
app.include_router(products_router.router, prefix="/products", tags=["Products"])