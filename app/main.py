from fastapi import FastAPI

from app.api import admin, health, resolve, search

app = FastAPI(
    title="BDPM Drug Resolver",
    description=(
        "Détection, recherche et correction de noms de médicaments français à "
        "partir de la Base de Données Publique des Médicaments (BDPM). "
        "Correspondance lexicale locale, sans dépendance externe au runtime — "
        "ne constitue pas une validation médicale ou pharmaceutique."
    ),
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(resolve.router)
app.include_router(admin.router)
