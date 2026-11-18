# Publicar la app en Streamlit Community Cloud (~5 minutos)

Requisitos: el repo `proyecto-economia-ecuador` en GitHub (público) con `app/data/*.parquet` ya versionado
(se genera al correr el pipeline).

1. Entra a **https://share.streamlit.io** e inicia sesión con tu cuenta de GitHub.
2. **Create app → Deploy a public app from GitHub.**
3. Completa:
   | Campo | Valor |
   |---|---|
   | Repository | `CarlosRomero55/proyecto-economia-ecuador` |
   | Branch | `main` |
   | Main file path | `app/streamlit_app.py` |
   | App URL | por ejemplo `ecuador-trade-monitor` |
4. **Advanced settings → Python version: 3.12.** No hace falta configurar *secrets*: la app no usa credenciales.
5. **Deploy.** Streamlit instala `app/requirements.txt` (está junto al archivo principal y tiene prioridad sobre el
   `requirements.txt` de la raíz, que incluye pyodbc y no se necesita en la nube).
6. Abre la URL en el celular y en el computador; cambia el idioma en la barra lateral.

## Después de publicar
- Reemplaza el marcador `APP_URL` en el `README.md` (insignia y enlace) y en `portfolio.json` → `app_url`.
- Cada `git push` a `main` redespliega la app. Para actualizar datos: corre el pipeline y haz commit de `app/data/`.

## Si falla
| Síntoma | Solución |
|---|---|
| "Todavía no hay datos" | Falta hacer commit de `app/data/*.parquet` |
| Error instalando pyodbc | Verifica que *Main file path* sea `app/streamlit_app.py` (así usa `app/requirements.txt`) |
| La app duerme | En el plan gratuito se suspende sin visitas; se reactiva con un clic |
