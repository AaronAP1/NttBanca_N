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
copy .env.example .env      # y completa las credenciales
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

## Lo que necesitas configurar en AWS

**RDS**
- El security group de la instancia debe permitir el puerto 5432 desde tu IP (o desde donde corra la API).
- Si te conectas desde tu PC, la instancia debe tener *Public access* habilitado o necesitas VPN/bastión.
- La base indicada en `DB_NAME` debe existir; las tablas se crean solas al arrancar.

**S3**: el usuario o rol IAM necesita como mínimo:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::MI-BUCKET" },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::MI-BUCKET/*"
    }
  ]
}
```

Si dejas `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` vacíos, boto3 usa `~/.aws/credentials` o el rol IAM de la máquina (EC2, ECS, Lambda), que es lo recomendado en producción.

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
