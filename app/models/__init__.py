# Importar aquí todos los modelos para que Base.metadata los registre.
from app.models.file import FileRecord
from app.models.item import Item

__all__ = ["FileRecord", "Item"]
