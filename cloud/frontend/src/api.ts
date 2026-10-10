export interface Config {
  supabaseUrl: string;
  publicKey: string;
  githubRepo: string;
}
export interface Session {
  access_token: string;
  refresh_token: string;
}
export interface Account {
  user_id: string;
  email: string;
  role: "admin" | "user";
  server_now: string;
  expires_at: string | null;
  revoked: boolean;
  active: boolean;
  remaining_seconds: number;
  share_measurements: boolean;
}
export interface Member {
  id: string;
  email: string;
  expires_at: string | null;
  revoked: boolean;
  active: boolean;
  share_measurements: boolean;
}
export interface Candidate {
  id: number;
  clone: string;
  mobile: string;
  shot: number;
  regime: string;
  contributors: number;
  source_count: number;
  status: "pending" | "published" | "rejected";
  fit: { holdout_speed_error: number };
  evidence: Record<string, unknown>;
}
export class Api {
  constructor(
    readonly config: Config,
    public session: Session | null = null,
  ) {}
  async request<T>(
    path: string,
    body: unknown,
    method = "POST",
    authenticated = true,
  ): Promise<T> {
    if (authenticated && !this.session) throw Error("Inicia sesión de nuevo.");
    const response = await fetch(this.config.supabaseUrl + path, {
      method,
      headers: {
        apikey: this.config.publicKey,
        "Content-Type": "application/json",
        ...(authenticated
          ? { Authorization: "Bearer " + this.session!.access_token }
          : {}),
      },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw Error(
        data?.message ||
          data?.error_description ||
          data?.msg ||
          data?.error ||
          "No se pudo conectar con el servidor.",
      );
    return data as T;
  }
  rpc<T>(action: string, args: Record<string, unknown> = {}): Promise<T> {
    return this.request<T>("/functions/v1/dragonlab-api", { action, args });
  }
  async login(email: string, password: string) {
    this.session = await this.request<Session>(
      "/auth/v1/token?grant_type=password",
      { email, password },
      "POST",
      false,
    );
    return this.rpc<Account>("my_account");
  }
  async refresh() {
    if (!this.session) throw Error("Sesión vencida");
    this.session = await this.request<Session>(
      "/auth/v1/token?grant_type=refresh_token",
      { refresh_token: this.session.refresh_token },
      "POST",
      false,
    );
    return this.rpc<Account>("my_account");
  }
}
export async function config(): Promise<Config> {
  const response = await fetch("/config.json", { cache: "no-store" });
  if (!response.ok) throw Error("Configura tu servidor Supabase.");
  const c = (await response.json()) as Config;
  if (
    !/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(c.supabaseUrl) ||
    !c.publicKey ||
    c.publicKey.includes("YOUR-") ||
    c.publicKey.startsWith("sb_secret_")
  )
    throw Error("Configura la dirección y la clave pública.");
  if (!c.publicKey.startsWith("sb_publishable_")) {
    try {
      if (
        JSON.parse(
          atob(c.publicKey.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
        ).role !== "anon"
      )
        throw Error();
    } catch {
      throw Error("Se requiere una clave pública anon.");
    }
  }
  return c;
}
