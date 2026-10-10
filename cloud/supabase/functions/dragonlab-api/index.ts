import { createHandler } from "./handler.ts";
Deno.serve(
  createHandler({
    url: Deno.env.get("SUPABASE_URL")!,
    publicKey: Deno.env.get("SUPABASE_ANON_KEY")!,
    panelOrigin:
      Deno.env.get("PANEL_ORIGIN") || "https://configure-your-panel.invalid",
  }),
);
