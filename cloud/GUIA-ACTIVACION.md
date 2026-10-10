# Activar DragonLab Cloud

El código está preparado. Todavía no existe un servidor de producción configurado: las vistas previas usan datos de ejemplo claramente identificados.

## 1. Crear Supabase

1. Entra en https://supabase.com y crea una cuenta; puedes usar GitHub. Crea una organización y un proyecto **Free**, por ejemplo `dragonlab`.
2. Elige una contraseña fuerte para la base de datos y guárdala en tu gestor de contraseñas. No la pongas en GitHub ni en el launcher.
3. En **SQL Editor**, abre una consulta, pega `cloud/supabase/migrations/001_accounts.sql` y ejecútala una sola vez. Crea las tablas y funciones de permisos.
4. En **Authentication → Users**, crea tu propia cuenta de correo y contraseña. Usa una contraseña de al menos 12 caracteres y marca el correo como confirmado. La creación de cuentas de esta versión es administrada, sin depender del envío de correos.
5. Copia el UUID de tu cuenta y ejecuta en SQL Editor:

```sql
insert into private.admins(user_id) values('TU-UUID-REAL');
```

Solo este paso inicial te convierte en administrador. Una cuenta normal no puede darse permisos.

6. Busca **Project URL** y la **publishable key**, o la clave heredada **anon**. Esos dos valores son públicos y se usan en el panel y el launcher. **Nunca uses service_role ni una clave sb_secret en ellos.**
7. Mantén el acceso por correo y contraseña activado. Si habilitas registro público, una cuenta nueva seguirá sin acceso hasta que tú le concedas meses. Esta interfaz no ofrece registro público.

## 2. Publicar el panel en Cloudflare Pages

1. Crea tu cuenta en https://dash.cloudflare.com y abre **Workers & Pages → Create → Pages → Connect to Git**.
2. Autoriza tu repositorio `leo10m2010/DragonLab`. Elige la rama que contiene este cambio, o `main` después de integrarlo.
3. Framework: **None**. Comando de compilación: `npm ci --prefix cloud/frontend && node cloud/write_config.mjs && npm run build --prefix cloud/frontend`. Carpeta de salida: `cloud/frontend/dist`. Directorio raíz: el repositorio. Añade `NODE_VERSION=22` a las variables de compilación.
4. Añade variables de compilación `SUPABASE_URL` y `SUPABASE_PUBLIC_KEY` con los valores públicos del paso anterior. No añadas la clave privada al panel.
5. Publica. Cloudflare te entrega una URL gratuita terminada en `.pages.dev`. Esa será tu panel de cuentas. Un dominio propio es opcional y puede tener coste.

El panel está escrito en React y TypeScript y se compila con Vite. También puedes desplegarlo en Netlify: el repositorio incluye `netlify.toml`; configura las mismas variables públicas. Incluye `vercel.json` para Vercel, pero un uso comercial requiere un plan que lo permita.

## 3. Activar el backend

La API `dragonlab-api` recibe las consultas del panel y del launcher y las dirige a funciones autorizadas de PostgreSQL. No permite ejecutar consultas o rutas arbitrarias. La función `admin-create-user` comprueba en el servidor si tu sesión pertenece a un administrador y luego crea una cuenta confirmada con acceso por meses. La clave privada se conserva dentro de Supabase.

Desde la carpeta `cloud`, con la CLI de Supabase disponible:

```text
npx supabase login
npx supabase link --project-ref TU-REFERENCIA-DEL-PROYECTO
npx supabase secrets set PANEL_ORIGIN=https://TU-PANEL.pages.dev
npx supabase functions deploy admin-create-user
npx supabase functions deploy dragonlab-api
```

El login de esa herramienta se hace en tu cuenta. No publiques su token. La referencia del proyecto es la primera parte de `TU-REFERENCIA.supabase.co`.

El backend usa Deno y TypeScript en Supabase Edge Functions. El archivo `supabase/config.toml` desactiva la validación JWT antigua del gateway para ambas funciones: **la sesión y los permisos se comprueban mediante el servidor y PostgreSQL en cada petición**. Configura `PANEL_ORIGIN` con la URL exacta del panel. Despliega ambos directorios con la CLI para incluir también `handler.ts`. No hace falta contratar un servidor permanente en Render para esta arquitectura.

## 4. Conectar GitHub y publicar el launcher

En **GitHub → Settings → Secrets and variables → Actions → Variables**, añade:

| Variable | Valor |
|---|---|
| SUPABASE_URL | URL pública de Supabase |
| SUPABASE_PUBLIC_KEY | publishable o anon; nunca service_role |
| PANEL_URL | URL HTTPS de Cloudflare Pages |

En **Secrets**, añade `SUPABASE_SERVICE_ROLE_KEY` únicamente para el trabajo de propuestas de calibración. Esta clave tiene privilegios de servidor. No se necesita en los ejecutables ni en la compilación del panel.

En **Actions → Publish Cloud release → Run workflow**, introduce una versión como `0.13.0`. El trabajo crea `DragonLab-Cloud.exe`, `dragonlab-release.json` y `DragonLab-Launcher.zip` y los publica juntos en una Release. No uses la misma versión para contenidos diferentes. Se comprueba SHA-256 antes de ejecutar una descarga. No es una firma digital de Windows.

Los usuarios descargan y extraen **DragonLab-Launcher.zip**. Contiene el launcher y la configuración pública. Al pulsar Abrir, el launcher descarga la versión Cloud de la última Release compatible. Las Releases deben conservar el manifest `dragonlab-release.json`; subir únicamente un exe suelto no basta.

## 5. Dar meses a un usuario

Entra en el panel con tu cuenta. En Administración pulsa **Crear cuenta**, indica correo, contraseña temporal y meses. Entrega esos datos al usuario por tu canal habitual; no hay envío automático de mensajes.

Una cuenta normal ve fecha de vencimiento, días completos restantes y, en el último día, horas/minutos. La hora procede del servidor. El usuario puede cambiar su contraseña. Añadir meses a un acceso activo conserva el tiempo restante; renovar uno vencido o suspendido comienza desde hoy. Se usan meses de calendario, no bloques fijos de 30 días. Suspender impide las nuevas consultas y el cliente Cloud lo detecta en su siguiente comprobación, aproximadamente un minuto.

El cliente Cloud requiere conexión al iniciar y comprueba el acceso durante el uso. Ante fallos de conexión transitorios permite como máximo diez minutos sin comprobarlo. Esta versión no concede meses ni permisos desde la PC.

## 6. Mediciones y calibraciones

Compartir mediciones viene desactivado. El aviso explica los datos: fuerza, velocidad, aceleración, viento, carro y modalidad. No se envían capturas, chats, nombres de jugadores ni historial del navegador. La cuenta identifica al colaborador en el servidor para limitar envíos y comprobar contribuyentes; no son datos totalmente anónimos.

Se envían lotes de hasta 50 muestras, máximo 1.000 al día por cuenta. No se atribuyen al usuario los datos antiguos incluidos en una instalación: solo se suben nuevos tiros observados durante su sesión. El usuario puede desactivar el envío y borrar sus muestras individuales. Los ajustes derivados ya publicados pueden continuar disponibles.

Cada seis horas, **Propose calibration improvements** analiza hasta las 10.000 muestras más recientes. Inicialmente genera candidatos de lanzamiento sin viento, por carro, modalidad y régimen de física. Requiere al menos tres participantes con seis tiros cada uno, fuerzas variadas y validación dejando fuera muestras y participantes. Tú decides si publicar el ajuste desde el panel. No afirma calibrar automáticamente todos los climas, SS especiales, Nak bajo tierra o persecución de Kalsiddon.

El cliente descarga ajustes publicados, pero solo aplica un perfil compartido cuando una medición local confirma condiciones compatibles. Un buen ajuste local tiene prioridad. Evita mezclar regímenes como ocurrió durante las partidas de Armor.

## Coste y límites

| Servicio | Uso | Plan inicial |
|---|---|---|
| Cloudflare Pages | Panel de cuentas y administrador | Free; hasta 500 compilaciones al mes |
| Supabase | Login, permisos, meses y mediciones | Free: 500 MB de base de datos, 50.000 usuarios activos mensuales, 5 GB de transferencia |
| GitHub Releases / Actions | Ejecutables, manifest y propuestas | Repositorio público; revisar sus condiciones y límites de uso |

Fuentes consultadas: https://developers.cloudflare.com/pages/platform/limits/ · https://supabase.com/pricing · https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

Supabase Free puede pausarse tras una semana de inactividad y no incluye copias automáticas de seguridad. Exporta la base antes de cambios importantes y vigila el tamaño de las mediciones. Una aplicación con muchos usuarios puede necesitar planes de pago; no se promete gratuidad ilimitada. Vercel Hobby restringe el uso a proyectos personales no comerciales: https://vercel.com/docs/plans/hobby.

No hay integración de pagos en esta versión: tú asignas los meses. Las versiones locales anteriores siguen siendo aplicaciones independientes; el control de acceso se aplica al nuevo ejecutable Cloud y al servidor. El servidor impide el acceso a datos sin licencia; ningún launcher puede garantizar que un cliente público no se modifique.

## Comprobaciones pendientes tras crear las cuentas

Probar login real, creación de una cuenta, renovación y suspensión, envío consentido desde dos PC, descarga de una Release real y publicación de un candidato. Las pruebas locales de permisos, caducidad, consentimiento y actualización no sustituyen esa validación en producción.
