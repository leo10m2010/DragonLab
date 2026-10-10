import React, { useEffect, useRef, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { Api, config, type Account, type Member, type Candidate } from "./api";
import "./style.css";
const preview = new URLSearchParams(location.search).get("preview");
const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "No se pudo completar la operación.";
const date = (v: string | null) =>
  v
    ? new Intl.DateTimeFormat("es-PE", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(v))
    : "Sin acceso asignado";
const fixture: Account = {
  user_id: "example",
  email: "jugador@ejemplo.com",
  role: preview === "admin" ? "admin" : "user",
  server_now: new Date().toISOString(),
  expires_at: new Date(Date.now() + 27 * 86400000).toISOString(),
  revoked: false,
  active: true,
  remaining_seconds: 27 * 86400,
  share_measurements: true,
};
function App() {
  const api = useRef<Api | null>(null);
  const [setup, setSetup] = useState(false);
  const [ready, setReady] = useState(!!preview);
  const [account, setAccount] = useState<Account | null>(
    preview ? fixture : null,
  );
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [clock, setClock] = useState(Date.now());
  const offset = useRef(0);
  const apply = (a: Account) => {
    offset.current = new Date(a.server_now).getTime() - Date.now();
    setAccount(a);
    setClock(Date.now());
  };
  useEffect(() => {
    if (preview) return;
    let alive = true;
    config()
      .then((c) => {
        if (alive) {
          api.current = new Api(c);
          setReady(true);
        }
      })
      .catch(() => {
        if (alive) setSetup(true);
      });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!account || preview) return;
    const timer = setInterval(() => {
      api.current
        ?.refresh()
        .then(apply)
        .catch(() => {
          setAccount(null);
          setMessage("Tu sesión venció. Vuelve a entrar.");
        });
    }, 5 * 60000);
    return () => clearInterval(timer);
  }, [!!account]);
  async function perform(work: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      if (preview)
        throw Error("Vista previa: las acciones están desactivadas.");
      await work();
    } catch (e) {
      setMessage(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const password = String(form.get("password"));
    await perform(async () =>
      apply(
        await api.current!.login(String(form.get("email")).trim(), password),
      ),
    );
  }
  const seconds = account
    ? Math.max(
        0,
        Math.floor(
          ((account.expires_at ? new Date(account.expires_at).getTime() : 0) -
            clock -
            offset.current) /
            1000,
        ),
      )
    : 0;
  const admin = account?.role === "admin";
  const active =
    admin || (!!account?.active && !account?.revoked && seconds > 0);
  return (
    <>
      <header>
        <a className="brand" href="./">
          <span className="symbol">↗</span>DragonLab
          <span className="brand-note">club de precisión</span>
        </a>
        <span className="pill">
          {preview
            ? "Vista previa"
            : account
              ? "Cuenta conectada"
              : ready
                ? "Listo para entrar"
                : "Sin configurar"}
        </span>
      </header>
      <main>
        {setup ? (
          <section className="card">
            <span className="eyebrow">PREPARADO PARA CONECTAR</span>
            <h2>Falta configurar el servidor</h2>
            <p>
              Necesitas la dirección y la clave pública de tu proyecto Supabase.
              La clave privada permanece en el servidor.
            </p>
            <a className="secondary" href="?preview=user">
              Ver cuenta de ejemplo
            </a>{" "}
            <a className="secondary" href="?preview=admin">
              Ver administración de ejemplo
            </a>
          </section>
        ) : !account ? (
          <section className="login">
            <div className="intro">
              <span className="eyebrow">TU PRÓXIMO TIRO, MÁS CLARO</span>
              <h1>
                Entra.
                <br />
                Apunta.
                <br />
                <em>Juega.</em>
              </h1>
              <p>
                Una cuenta para tu acceso, tus actualizaciones y una guía que
                mejora con cada partida.
              </p>
              <div className="trajectory" aria-hidden>
                <svg viewBox="0 0 430 130">
                  <path d="M15 110Q220-95 410 110" />
                  <circle cx="410" cy="110" r="7" />
                  <path className="ground" d="M0 120H430" />
                </svg>
              </div>
            </div>
            <form className="card login-card" onSubmit={login}>
              <span className="eyebrow">BIENVENIDO DE NUEVO</span>
              <h2>Tu cuenta</h2>
              <label>
                Correo
                <input
                  name="email"
                  type="email"
                  autoComplete="username"
                  required
                  placeholder="tu@correo.com"
                />
              </label>
              <label>
                Contraseña
                <input
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  minLength={8}
                  placeholder="Tu contraseña"
                />
              </label>
              <button className="primary" disabled={busy || !ready}>
                Entrar <span>↗</span>
              </button>
              <p className="small">
                Tu administrador crea tu cuenta y activa el tiempo de acceso.
              </p>
              <div role="status" className="message">
                {message}
              </div>
            </form>
          </section>
        ) : (
          <>
            <div className="section-heading">
              <div>
                <span className="eyebrow">TODO LISTO PARA JUGAR</span>
                <h1>Hola, {account.email.split("@")[0]}.</h1>
              </div>
              <button
                className="quiet"
                onClick={() =>
                  perform(async () => {
                    await api.current!.request("/auth/v1/logout", {});
                    api.current!.session = null;
                    setAccount(null);
                  })
                }
              >
                Cerrar sesión
              </button>
            </div>
            <div className="account-grid">
              <article className="card pass">
                <span className="eyebrow">TU ACCESO</span>
                <span className={"pill" + (!active ? " warning" : "")}>
                  {admin
                    ? "Administrador"
                    : account.revoked
                      ? "Suspendido"
                      : active
                        ? "Acceso activo"
                        : "Acceso vencido"}
                </span>
                <div className="remaining">
                  <strong>{admin ? "∞" : Math.floor(seconds / 86400)}</strong>
                  <span>
                    {admin
                      ? "administrador"
                      : seconds < 86400 && active
                        ? `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min disponibles`
                        : "días completos disponibles"}
                  </span>
                </div>
                <p>
                  {admin
                    ? "Puedes gestionar las cuentas y los perfiles."
                    : `Vence el ${date(account.expires_at)}`}
                </p>
                <div className="pass-footer">
                  <span>Tiempo comprobado por el servidor</span>
                  <span className="symbol">↗</span>
                </div>
              </article>
              <div className="side-stack">
                <article className="card download">
                  <span className="eyebrow">DRAGONLAB PARA WINDOWS</span>
                  <h2>
                    Tu partida.
                    <br />
                    Tu guía.
                  </h2>
                  <p>
                    El launcher comprueba tu acceso y mantiene el programa al
                    día.
                  </p>
                  <a
                    className="primary"
                    target="_blank"
                    rel="noopener"
                    href="https://github.com/leo10m2010/DragonLab/releases/latest"
                  >
                    Descargar launcher <span>↓</span>
                  </a>
                  <span className="small">
                    Las versiones se publican en GitHub.
                  </span>
                </article>
                <article className="card contribution">
                  <div className="row">
                    <h3>Mejoramos juntos</h3>
                    <label className="switch">
                      <input
                        type="checkbox"
                        aria-label="Compartir mediciones"
                        checked={account.share_measurements}
                        disabled={busy}
                        onChange={(e) => {
                          const enabled = e.target.checked;
                          perform(async () => {
                            await api.current!.rpc("set_measurement_consent", {
                              enabled,
                              erase_existing: false,
                            });
                            apply(
                              await api.current!.rpc<Account>("my_account"),
                            );
                          });
                        }}
                      />
                      <span />
                    </label>
                  </div>
                  <p>
                    Si lo activas, compartes fuerza, ángulo, viento y movimiento
                    de los proyectiles para mejorar las calibraciones. No se
                    envían capturas, chats ni nombres de jugadores.
                  </p>
                  <p className="small">
                    Puedes desactivarlo cuando quieras. Los ajustes derivados ya
                    publicados pueden seguir disponibles.
                  </p>
                  <button
                    className="text-button"
                    onClick={() =>
                      perform(async () => {
                        if (
                          !confirm(
                            "¿Desactivar y borrar tus mediciones individuales? Los ajustes publicados permanecen disponibles.",
                          )
                        )
                          return;
                        await api.current!.rpc("set_measurement_consent", {
                          enabled: false,
                          erase_existing: true,
                        });
                        apply(await api.current!.rpc<Account>("my_account"));
                        setMessage("Envío desactivado y mediciones borradas.");
                      })
                    }
                  >
                    Desactivar y borrar mis mediciones
                  </button>
                </article>
              </div>
            </div>
            <section className="card password-card">
              <div>
                <h3>Cambiar contraseña</h3>
                <p className="small">
                  Usa una contraseña propia después del primer acceso.
                </p>
              </div>
              <form
                id="change-password"
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget;
                  const data = new FormData(form);
                  perform(async () => {
                    await api.current!.request(
                      "/auth/v1/user",
                      { password: data.get("password") },
                      "PUT",
                    );
                    form.reset();
                    setMessage("Contraseña actualizada.");
                  });
                }}
              >
                <label className="sr-only" htmlFor="new-password">
                  Nueva contraseña
                </label>
                <input
                  id="new-password"
                  name="password"
                  type="password"
                  minLength={12}
                  required
                  autoComplete="new-password"
                  placeholder="Nueva contraseña · mínimo 12 caracteres"
                />
                <button className="secondary" disabled={busy}>
                  Guardar
                </button>
              </form>
            </section>
            {admin && <Admin api={api.current} onError={setMessage} />}
            <div role="status" className="message">
              {message}
            </div>
          </>
        )}
      </main>
      <footer>
        <span>DragonLab · precisión que se comparte.</span>
        <span>{preview ? "Datos de ejemplo · sin conexión" : ""}</span>
      </footer>
    </>
  );
}
function Admin({
  api,
  onError,
}: {
  api: Api | null;
  onError: (s: string) => void;
}) {
  const [users, setUsers] = useState<Member[]>(
    preview
      ? [
          {
            id: "example",
            email: "jugador@ejemplo.com",
            expires_at: fixture.expires_at,
            revoked: false,
            active: true,
            share_measurements: true,
          },
          {
            id: "example2",
            email: "otro@ejemplo.com",
            expires_at: new Date(Date.now() - 86400000).toISOString(),
            revoked: false,
            active: false,
            share_measurements: false,
          },
        ]
      : [],
  );
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const load = async () => {
    if (preview) return;
    const [u, c] = await Promise.all([
      api!.rpc<Member[]>("admin_users", { page_offset: page * 50 }),
      api!.rpc<Candidate[]>("admin_candidates"),
    ]);
    setUsers(u);
    setCandidates(c);
  };
  useEffect(() => {
    load().catch((e) => onError(errorText(e)));
  }, [page]);
  const action = async (work: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    try {
      if (preview)
        throw Error("Vista previa: las acciones están desactivadas.");
      await work();
      await load();
    } catch (e) {
      onError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section id="admin">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SOLO PARA TI</span>
          <h2>Administración</h2>
        </div>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => action(load)}
        >
          Actualizar
        </button>
      </div>
      <div className="card">
        <div className="row">
          <h3>Usuarios y acceso</h3>
          <button
            className="secondary"
            onClick={() =>
              preview
                ? onError("Vista previa: no crea cuentas.")
                : dialog.current!.showModal()
            }
          >
            Crear cuenta +
          </button>
        </div>
        <p className="small">
          Una renovación suma meses al vencimiento vigente. Un acceso vencido o
          suspendido comienza desde hoy.
        </p>
        <div className="users">
          {users.map((user) => (
            <User
              key={user.id}
              user={user}
              busy={busy}
              renew={(months) =>
                action(() =>
                  api!.rpc("admin_grant", {
                    target: user.id,
                    months,
                    request_id: crypto.randomUUID(),
                  }),
                )
              }
              suspend={() =>
                action(async () => {
                  if (confirm("¿Suspender " + user.email + "?"))
                    await api!.rpc("admin_revoke", {
                      target: user.id,
                      request_id: crypto.randomUUID(),
                    });
                })
              }
            />
          ))}
          {!users.length && <p>No hay usuarios en esta página.</p>}
        </div>
        <div className="row pagination">
          <button
            className="quiet"
            disabled={!page || busy}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </button>
          <span className="small">Página {page + 1}</span>
          <button
            className="quiet"
            disabled={users.length < 50 || busy}
            onClick={() => setPage(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
      <div className="card calibration-card">
        <h3>Calibraciones propuestas</h3>
        <p>
          Las mediciones se comprueban automáticamente. Revisa el ajuste antes
          de compartirlo con todos.
        </p>
        {!candidates.length ? (
          <p className="small">Todavía no hay ajustes listos para revisar.</p>
        ) : (
          candidates.map((c) => (
            <article className="candidate" key={c.id}>
              <h3>
                {c.mobile} · {c.shot === 2 ? "SS" : `tiro ${c.shot + 1}`}
              </h3>
              <p>
                {c.clone} · {c.source_count} tiros · {c.contributors}{" "}
                participantes · {c.regime}
              </p>
              <p className="small">
                Error máximo: {c.fit.holdout_speed_error.toFixed(2)} ·{" "}
                {c.status}
              </p>
              {c.status === "pending" && (
                <div className="row">
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      action(() =>
                        api!.rpc("admin_publish", {
                          candidate: c.id,
                          approved: true,
                        }),
                      )
                    }
                  >
                    Publicar ajuste
                  </button>
                  <button
                    className="quiet"
                    disabled={busy}
                    onClick={() =>
                      action(() =>
                        api!.rpc("admin_publish", {
                          candidate: c.id,
                          approved: false,
                        }),
                      )
                    }
                  >
                    Descartar
                  </button>
                </div>
              )}
            </article>
          ))
        )}
      </div>
      <dialog ref={dialog}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const f = new FormData(form);
            action(async () => {
              await api!.rpc("create_user", {
                email: f.get("email"),
                password: f.get("password"),
                months: Number(f.get("months")),
                request_id: crypto.randomUUID(),
              });
              form.reset();
              dialog.current!.close();
            });
          }}
        >
          <span className="eyebrow">NUEVA CUENTA</span>
          <h2>Dale acceso.</h2>
          <label>
            Correo
            <input name="email" type="email" required autoComplete="off" />
          </label>
          <label>
            Contraseña temporal
            <input
              name="password"
              type="password"
              minLength={12}
              required
              autoComplete="new-password"
            />
          </label>
          <label>
            Meses de acceso
            <select name="months">
              {[1, 2, 3, 6, 12].map((m) => (
                <option key={m} value={m}>
                  {m} {m === 1 ? "mes" : "meses"}
                </option>
              ))}
            </select>
          </label>
          <div className="row">
            <button
              type="button"
              className="quiet"
              onClick={() => dialog.current!.close()}
            >
              Cancelar
            </button>
            <button className="primary" disabled={busy}>
              Crear cuenta
            </button>
          </div>
        </form>
      </dialog>
    </section>
  );
}
function User({
  user,
  busy,
  renew,
  suspend,
}: {
  user: Member;
  busy: boolean;
  renew: (months: number) => Promise<void>;
  suspend: () => Promise<void>;
}) {
  const [months, setMonths] = useState(1);
  return (
    <article className="user-row">
      <div>
        <div className="user-email">{user.email}</div>
        <div className="small">
          {user.revoked
            ? "Suspendido"
            : user.active
              ? "Activo"
              : "Sin acceso activo"}
        </div>
      </div>
      <div className="small">{date(user.expires_at)}</div>
      <div className="user-actions">
        <select
          aria-label={"Meses para " + user.email}
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
        >
          {[1, 2, 3, 6, 12].map((m) => (
            <option key={m} value={m}>
              {m} {m === 1 ? "mes" : "meses"}
            </option>
          ))}
        </select>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => renew(months)}
        >
          Añadir
        </button>
        <button className="quiet" disabled={busy} onClick={suspend}>
          Suspender
        </button>
      </div>
    </article>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
