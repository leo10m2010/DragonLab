export interface Environment {
  url: string;
  publicKey: string;
  panelOrigin: string;
}
const actions = new Set([
  "my_account",
  "set_measurement_consent",
  "admin_users",
  "admin_grant",
  "admin_revoke",
  "ingest_measurements",
  "published_calibrations",
  "admin_candidates",
  "admin_publish",
]);
export function createHandler(env: Environment, fetcher: typeof fetch = fetch) {
  return async (request: Request): Promise<Response> => {
    const headers = {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": env.panelOrigin,
      "Access-Control-Allow-Headers": "authorization,apikey,content-type",
      "Access-Control-Allow-Methods": "POST,OPTIONS",
      Vary: "Origin",
      "Cache-Control": "no-store",
    };
    const response = (value: unknown, status = 200) =>
      new Response(JSON.stringify(value), { status, headers });
    if (request.method === "OPTIONS") return new Response(null, { headers });
    if (request.method !== "POST")
      return response({ error: "Método no disponible" }, 405);
    const authorization = request.headers.get("authorization") || "";
    if (!/^Bearer \S+$/.test(authorization))
      return response({ error: "Inicia sesión" }, 401);
    try {
      if (Number(request.headers.get("content-length") || 0) > 100000)
        return response({ error: "Petición demasiado grande" }, 413);
      const raw = await request.text();
      if (raw.length > 100000)
        return response({ error: "Petición demasiado grande" }, 413);
      const body = JSON.parse(raw) as {
        action?: string;
        args?: Record<string, unknown>;
      };
      if (
        typeof body.action !== "string" ||
        (!actions.has(body.action) && body.action !== "create_user")
      )
        return response({ error: "Acción no disponible" }, 404);
      if (
        body.args !== undefined &&
        (body.args === null ||
          typeof body.args !== "object" ||
          Array.isArray(body.args))
      )
        return response({ error: "Argumentos inválidos" }, 400);
      const path =
        body.action === "create_user"
          ? "/functions/v1/admin-create-user"
          : "/rest/v1/rpc/" + body.action;
      const result = await fetcher(env.url + path, {
        method: "POST",
        headers: {
          apikey: env.publicKey,
          Authorization: authorization,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body.args || {}),
      });
      const value = await result.json().catch(() => null);
      // PostgreSQL authenticates the JWT and checks role, access and row ownership.
      return response(value, result.status === 204 ? 200 : result.status);
    } catch {
      return response({ error: "No se pudo completar la petición" }, 400);
    }
  };
}
