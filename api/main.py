"""FastAPI — CerradoWatch REST API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import clima, desmatamento, kpis, queimadas

app = FastAPI(
    title="CerradoWatch API",
    description=(
        "API REST para dados ambientais do Cerrado brasileiro: "
        "queimadas (NASA FIRMS), desmatamento (PRODES/INPE), "
        "clima (INMET) e preços de commodities (CONAB)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(queimadas.router)
app.include_router(desmatamento.router)
app.include_router(clima.router)
app.include_router(kpis.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "project": "CerradoWatch"}
