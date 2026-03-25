import { SessionOptions, getIronSession } from "iron-session";
import { cookies } from "next/headers";

export interface AppSession {
  userId?: string;
  tenantId?: string;
  email?: string;
  role?: string;
  fullName?: string;
  oauthState?: string;
  oauthTenantId?: string;
  oauthNext?: string;
}

const secret = process.env.SESSION_SECRET || "dev-only-super-secret-key-32-chars-min";

export const sessionOptions: SessionOptions = {
  password: secret,
  cookieName: "agente_vendedor_session",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
  },
};

export async function getSession() {
  return getIronSession<AppSession>(await cookies(), sessionOptions);
}
