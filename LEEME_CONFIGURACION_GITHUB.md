# Observatorio de precios ONT/FTTH • México (nube)

**Objetivo:** monitorear precios públicos de ONT/ONU para FTTH en México y publicar un dashboard web con histórico semanal. Datos iniciales: 23-11-2026 (75 ofertas / 37 modelos / 7 portales con precios). Los importes iniciales provienen del corte del observatorio anterior: **no se revalidaron al elaborar este kit**.

## Implementación recomendada: GitHub + GitHub Pages

### 1. Crear tu cuenta y repositorio
1. Abre https://github.com y crea/inicia sesión en tu cuenta.
2. Instala GitHub Desktop desde https://desktop.github.com/ (sirve para subir las carpetas ocultas `.github/` sin usar comandos).
3. Extrae este ZIP a una carpeta nueva llamada `observatorio-ont-ftth`.
4. Abre GitHub Desktop > **File > Add local repository... > Choose...** y selecciona esa carpeta.
5. Si GitHub Desktop indica que no es un repositorio Git, elige **create a repository here**; indica `observatorio-ont-ftth`, confirma y luego selecciona **Commit to main** para guardar los archivos.
6. Haz clic en **Publish repository** y deja la casilla `Keep this code private` **DESACTIVADA** si usarás GitHub Free + GitHub Pages público.
7. Revisa el repositorio en github.com; confirma que exista `.github/workflows/observatorio_ont_ftth.yml` y que los archivos no hayan quedado dentro de otra subcarpeta adicional.

> Atención: un repositorio público y el sitio Pages exponen la base de datos y el histórico a cualquier persona. No incluyas costos negociados, claves, datos personales ni información interna. La modalidad privada requiere otra arquitectura/plan según permisos.

### 2. Activar publicación
1. En GitHub abre el repositorio y ve a **Settings > Pages**.
2. En **Build and deployment > Source**, selecciona **GitHub Actions**.
3. En **Settings > Actions > General > Workflow permissions**, el flujo ya solicita `contents: write` para guardar los cambios; si tu cuenta/organización lo restringe, habilita **Read and write permissions** para el token o solicita al administrador el permiso.
4. En la pestaña **Actions**, abre `ONT FTTH | monitoreo y dashboard semanal` y pulsa **Run workflow** en la rama `main`.
5. Comprueba dos jobs exitosos: `actualizar` y `publicar`. Puede haber capturas `NO VERIFICABLE`: no significa que se hayan fabricado precios; revisa los registros del job.

### 3. Consultar el dashboard
Al publicarse, el enlace normalmente será:
`https://TU-USUARIO.github.io/observatorio-ont-ftth/`
(Cambia TU-USUARIO por tu usuario y verifica la URL definitiva en **Settings > Pages** o en el job `publicar`.)

### 4. Frecuencia y datos
- Se ejecuta **cada lunes a las 09:15 hora Ciudad de México** según `.github/workflows/observatorio_ont_ftth.yml`.
- GitHub Actions puede retrasar ejecuciones o no ejecutar alguna por congestión. Revísalas en la pestaña Actions.
- El repositorio conservará cada semana `Historico_ONT_FTTH_2026.csv`, `Log_Actualizaciones_ONT.csv` y `Estado_Monitoreo_ONT.json`.
- El sitio `sitio/index.html` publica el dashboard, `sitio/historico_ont_ftth.csv` el histórico y `sitio/estado_monitoreo.json` el diagnóstico de última corrida.
- Si el sitio cambia su estructura, exige login o bloquea bots, el rastreo NO añade un precio nuevo y deja `NO VERIFICABLE` en el log.
- El archivo `Observatorio_ONT_FTTH_Mexico_2026.xlsx` sigue siendo una **instantánea inicial**; para datos nuevos descarga el CSV del sitio y ábrelo en Excel.
- El histórico conserva los registros previos y omite capturas duplicadas del mismo día para cada par proveedor/modelo.

### 5. Cómo comprobar la primera semana
- En **Actions**, confirma que la ejecución del lunes finalizó y que no hubo error de la publicación.
- Abre el dashboard, revisa la barra **Última ejecución**, el número de capturas y los casos no verificables.
- En **Histórico semanal**, selecciona un SKU, por ejemplo Huawei EG8145V5, y un proveedor para comparar fechas.
- Si hay cero precios nuevos, el sistema NO inventó valores; revisa `Log_Actualizaciones_ONT.csv` para identificar los portales que requieren adaptación.
- En repositorios públicos, GitHub puede deshabilitar tareas programadas por 60 días de inactividad; revisa la pestaña Actions y reactivarlas si fuera necesario.

## Estructura incluida
- `Actualizar_ONT_FTTH.py`: reconsulta fuentes y publica el sitio estático. Sólo biblioteca estándar Python.
- `Fuentes_Rastreo_ONT_FTTH.csv`: 75 referencias originales (SKU + proveedor + URL + modo de extracción).
- `Historico_ONT_FTTH_2026.csv`: base histórica inicial.
- `Plantilla_Dashboard_ONT.html`: plantilla del dashboard.
- `.github/workflows/observatorio_ont_ftth.yml`: programación y publicación.
- `sitio/`: archivos públicos que se publican mediante GitHub Pages.

## Prueba sin internet
En consola ejecuta: `python Actualizar_ONT_FTTH.py --solo-publicar`.
No modifica el CSV: sólo reconstruye `sitio/index.html` y las descargas públicas desde la base existente.

## Precauciones
- Los precios públicos son informativos, no se garantizan inventario, impuestos, envío ni precio de checkout.
- No es un crawler completo de todas las tiendas en México: monitorea las URLs de la base; ampliar cobertura exige añadir y probar fuentes.
- El precio para múltiples variantes Shopify se toma de la variante disponible más barata: exige validar que variantes representen el mismo SKU antes de tomar decisiones.
- Este kit NO se ha desplegado en tu cuenta GitHub: la conexión/autorización y publicación se deben completar en tu cuenta.
