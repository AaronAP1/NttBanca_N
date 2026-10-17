# NttBanca API

API en FastAPI sobre PostgreSQL (AWS RDS) y S3.

- **Items**: entidades de negocio en la tabla `items`.
- **Files**: cada archivo se guarda en S3 y la tabla `files` guarda un registro que **apunta** al objeto
  (`bucket` + `s3_key`) junto con sus metadatos. Un archivo puede pertenecer a un item o estar suelto.

## Tablas

```
items                              files
─────────────────────              ──────────────────────────────────────────
id            SERIAL  PK  ◄─┐      id                 SERIAL   PK
name          VARCHAR(255)  └───── item_id            INTEGER  FK → items.id (ON DELETE CASCADE), nullable
description   TEXT                 bucket             VARCHAR(63)   ┐ puntero al objeto en S3
is_active     BOOLEAN              s3_key             VARCHAR(1024) ┘ UNIQUE (bucket, s3_key)
created_at    TIMESTAMPTZ          original_filename  VARCHAR(255)   nombre con el que se subió
updated_at    TIMESTAMPTZ          content_type       VARCHAR(255)
                                   size_bytes         BIGINT
                                   etag               VARCHAR(255)
                                   created_at / updated_at  TIMESTAMPTZ
```

Las tablas se crean solas al arrancar (`DB_AUTO_CREATE_TABLES=true`).

### Consistencia entre S3 y la BD

Un registro de `files` nunca apunta a un objeto inexistente:

- **Subir / reemplazar**: primero se sube a S3 y luego se guarda en la BD. Si la BD falla, se borra lo subido.
  Al reemplazar se usa una key nueva y el objeto anterior se borra solo después del commit.
- **Borrar** (un archivo o un item con sus archivos): primero la BD, luego S3. Si S3 falla, el objeto queda
  huérfano en el bucket y se registra en el log, pero ningún registro lo referencia.

Las keys se generan como `S3_KEY_PREFIX/<uuid>.<ext>`; el nombre original vive en la BD y se usa al descargar.

## Estructura

```
app/
├── main.py              # crea la app, registra routers y crea tablas al arrancar
├── core/config.py       # configuración leída del .env (pydantic-settings)
├── db/                  # engine, sesión y Base de SQLAlchemy
├── models/              # modelos ORM: Item, FileRecord
├── schemas/             # modelos Pydantic de entrada/salida
├── crud/                # consultas a Postgres
├── services/s3.py       # cliente y operaciones sobre S3
├── services/files.py    # operaciones que tocan S3 + BD a la vez
└── api/routes/          # endpoints: health, items, files
tests/                   # tests con SQLite en memoria + moto (S3 simulado)
```

## Puesta en marcha

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # y completa las credenciales (ver docs/SETUP_AWS.md)
fastapi dev app/main.py
```

Documentación interactiva: http://127.0.0.1:8000/docs

Para comprobar las conexiones:

- `GET /health/db`: ejecuta `SELECT 1` contra RDS.
- `GET /health/s3`: hace `head_bucket` sobre el bucket configurado.

## Endpoints

### Items

| Método | Ruta                 | Descripción                                        |
|--------|----------------------|----------------------------------------------------|
| POST   | `/items`             | Crear                                              |
| GET    | `/items`             | Listar (`skip`, `limit`)                           |
| GET    | `/items/{id}`        | Obtener uno                                        |
| GET    | `/items/{id}/files`  | Archivos del item                                  |
| PATCH  | `/items/{id}`        | Actualizar campos parcialmente                     |
| DELETE | `/items/{id}`        | Eliminar el item, sus registros y sus objetos en S3 |

### Files

| Método | Ruta                          | Descripción                                                  |
|--------|-------------------------------|--------------------------------------------------------------|
| POST   | `/files`                      | Subir (multipart: `file`, `item_id` opcional)                |
| GET    | `/files`                      | Listar registros (`item_id`, `skip`, `limit`)                |
| GET    | `/files/{id}`                 | Obtener el registro                                          |
| GET    | `/files/{id}/download`        | Descargar desde S3 (streaming, con el nombre original)       |
| GET    | `/files/{id}/presigned-url`   | URL temporal de descarga directa desde S3 (`expires_in`)     |
| PUT    | `/files/{id}`                 | Reemplazar el contenido (multipart: `file`)                  |
| PATCH  | `/files/{id}`                 | Cambiar `original_filename` o `item_id` (null = desvincular) |
| DELETE | `/files/{id}`                 | Eliminar registro y objeto en S3                             |

## Configurar AWS

La guía paso a paso para crear el bucket de S3, el usuario IAM y la base PostgreSQL en RDS, llenar el `.env` y
probar el backend está en **[docs/SETUP_AWS.md](docs/SETUP_AWS.md)**.

Para crear todo de una vez desde la terminal (en Windows, Git Bash), con el AWS CLI ya configurado:

```bash
bash scripts/aws_setup_dev.sh
```

## Desplegar en EC2

Para publicar la API en una EC2 junto a la RDS, de modo que otros puedan consumirla, sigue
**[docs/DEPLOY_EC2.md](docs/DEPLOY_EC2.md)**. En resumen:

```bash
bash scripts/aws_deploy_ec2.sh
```

Para publicar cambios del código, vuelve a correr el mismo comando.

## Tests

No necesitan credenciales: usan SQLite en memoria y S3 simulado con moto.

```powershell
pip install -r requirements-dev.txt
pytest
```

## Próximos pasos sugeridos

- Reemplazar `create_all` por migraciones con Alembic cuando el esquema empiece a cambiar.
- Renombrar/duplicar `Item` según las entidades reales del negocio.
- Agregar autenticación a los endpoints.
