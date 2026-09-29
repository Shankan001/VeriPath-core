// supabase/functions/send-otp-sms/index.ts
import { Webhook } from "https://esm.sh/standardwebhooks@1.0.0";

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("not allowed", { status: 405 });
  }

  const rawBody = await req.text();
  const headers = Object.fromEntries(req.headers);

  const hookSecret = (Deno.env.get("SEND_SMS_HOOK_SECRET") ?? "").replace("v1,whsec_", "");
  if (!hookSecret) {
    console.error("SEND_SMS_HOOK_SECRET not configured");
    return new Response(JSON.stringify({ error: "not configured" }), { status: 500 });
  }

  let event: any;
  try {
    const wh = new Webhook(hookSecret);
    event = wh.verify(rawBody, headers);
  } catch (err) {
    console.error("Signature verification failed:", err);
    return new Response(JSON.stringify({ error: "invalid signature" }), { status: 401 });
  }

  try {
    const to = event.user?.phone;
    const message = `Your VeriPath verification code is ${event.sms?.otp}. Valid for 5 minutes.`;

    if (!to) {
      return new Response(JSON.stringify({ error: "missing phone number" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const apiKey = Deno.env.get("AT_API_KEY");
    const username = Deno.env.get("AT_USERNAME") ?? "sandbox";
    const baseUrl = Deno.env.get("AT_BASE_URL") ??
      "https://api.sandbox.africastalking.com/version1/messaging";

    console.log("AT config check - username:", username, "baseUrl:", baseUrl, "apiKey present:", !!apiKey, "apiKey length:", apiKey?.length ?? 0);

    if (!apiKey) {
      return new Response(JSON.stringify({ error: "AT_API_KEY not configured" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    const form = new URLSearchParams();
    form.set("username", username);
    form.set("to", to);
    form.set("message", message);

    const atResponse = await fetch(baseUrl, {
      method: "POST",
      headers: {
        "apiKey": apiKey,
        "Accept": "application/json",
      },
      body: form,
    });

    // Read as text first — AT sometimes returns plain-text errors, not JSON.
    const rawText = await atResponse.text();
    console.log("AT raw response status:", atResponse.status, "body:", rawText);

    let atResult: any;
    try {
      atResult = JSON.parse(rawText);
    } catch {
      atResult = { raw: rawText };
    }

    if (!atResponse.ok) {
      console.error("Africa's Talking error:", atResult);
      return new Response(JSON.stringify({ error: "sms send failed", details: atResult }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error(err);
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
