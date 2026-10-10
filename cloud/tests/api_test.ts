import { createHandler } from "../supabase/functions/dragonlab-api/handler.ts";
function assert(value: unknown, message: string) {
  if (!value) throw Error(message);
}
const env = {
  url: "https://fixture.supabase.co",
  publicKey: "fixture-public",
  panelOrigin: "https://fixture.pages.dev",
};
Deno.test(
  "API rejects missing sessions and unknown actions before upstream access",
  async () => {
    let calls = 0;
    const handler = createHandler(env, async () => {
      calls++;
      return new Response("{}");
    });
    const unauth = await handler(
      new Request("https://fixture.test", { method: "POST", body: "{}" }),
    );
    assert(unauth.status === 401, "anonymous rejected");
    const unknown = await handler(
      new Request("https://fixture.test", {
        method: "POST",
        headers: { Authorization: "Bearer fixture" },
        body: JSON.stringify({ action: "execute_arbitrary_sql" }),
      }),
    );
    assert(unknown.status === 404, "unknown action rejected");
    assert(calls === 0, "no upstream action");
  },
);
Deno.test(
  "API forwards user JWT and lets the database enforce permissions",
  async () => {
    const handler = createHandler(env, async (url, options) => {
      assert(
        String(url) === "https://fixture.supabase.co/rest/v1/rpc/admin_users",
        "only fixed RPC path",
      );
      assert(
        new Headers(options?.headers).get("Authorization") === "Bearer fixture",
        "JWT preserved",
      );
      return new Response(JSON.stringify({ message: "Solo administrador" }), {
        status: 403,
      });
    });
    const result = await handler(
      new Request("https://fixture.test", {
        method: "POST",
        headers: { Authorization: "Bearer fixture" },
        body: JSON.stringify({
          action: "admin_users",
          args: { page_offset: 0 },
        }),
      }),
    );
    assert(result.status === 403, "server rejection preserved");
    assert(
      result.headers.get("Access-Control-Allow-Origin") === env.panelOrigin,
      "CORS exact",
    );
  },
);
Deno.test(
  "API rejects oversized or malformed JSON without forwarding",
  async () => {
    let calls = 0;
    const handler = createHandler(env, async () => {
      calls++;
      return new Response("{}");
    });
    for (const raw of ["{", "x".repeat(100001)]) {
      const result = await handler(
        new Request("https://fixture.test", {
          method: "POST",
          headers: { Authorization: "Bearer fixture" },
          body: raw,
        }),
      );
      assert(
        result.status === 400 || result.status === 413,
        "invalid input rejected",
      );
    }
    assert(calls === 0, "nothing forwarded");
  },
);
