from app.api.demo import isolation_forest, kmeans, lstm
from app.api.demo.router import router

_registered_route_modules = (isolation_forest, kmeans, lstm)

__all__ = ["router"]