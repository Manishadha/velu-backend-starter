from __future__ import annotations

from typing import Any, Dict, List
import json


def _norm_str(value: Any, default: str = "") -> str:
    s = str(value or "").strip()
    return s or default


def _extract_locales_from_blueprint(bp: Any) -> List[str] | None:
    if isinstance(bp, dict):
        loc = bp.get("localization") or {}
        if isinstance(loc, dict):
            supported = loc.get("supported_languages")
            default = loc.get("default_language")
            out: List[str] = []
            if isinstance(supported, (list, tuple)):
                out = [str(x) for x in supported if str(x).strip()]
            if not out and isinstance(default, str) and default.strip():
                out = [default.strip()]
            return out or None

    localization = getattr(bp, "localization", None)
    if localization is not None:
        supported = getattr(localization, "supported_languages", None)
        default = getattr(localization, "default_language", None)
        out: List[str] = []
        if isinstance(supported, (list, tuple)):
            out = [str(x) for x in supported if str(x).strip()]
        if not out and isinstance(default, str) and default.strip():
            out = [default.strip()]
        return out or None

    return None


def _extract_locales(payload: Dict[str, Any]) -> List[str]:
    bp = payload.get("blueprint")
    if bp is not None:
        from_bp = _extract_locales_from_blueprint(bp)
        if from_bp:
            return from_bp

    raw_locales = payload.get("locales")
    if isinstance(raw_locales, (list, tuple)) and raw_locales:
        return [str(x) for x in raw_locales if str(x).strip()]

    product = payload.get("product")
    if isinstance(product, dict):
        prod_locales = product.get("locales")
        if isinstance(prod_locales, (list, tuple)) and prod_locales:
            return [str(x) for x in prod_locales if str(x).strip()]

    return ["en"]


def _extract_name_and_kind(payload: Dict[str, Any]) -> tuple[str, str]:
    bp = payload.get("blueprint")
    if bp is not None:
        if isinstance(bp, dict):
            name = _norm_str(bp.get("name"), "Product")
            kind = _norm_str(bp.get("kind"), "web_app")
            return name, kind
        name = _norm_str(getattr(bp, "name", None), "Product")
        kind = _norm_str(getattr(bp, "kind", None), "web_app")
        return name, kind

    product = payload.get("product") or {}
    if isinstance(product, dict):
        name = _norm_str(product.get("name"), "Product")
    else:
        name = "Product"

    kind = "web_app"
    return name, kind


def _chat_widget_tsx(api_path: str = "/v1/ai/chat") -> str:
    tpl = """
import React, { useState } from "react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export function VeluChatWidget() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) {
      return;
    }
    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: text },
    ];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const res = await fetch("__API_PATH__", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });
      if (!res.ok) {
        throw new Error("http");
      }
      const data = await res.json();
      const assistantText =
        (data && data.message && data.message.content) ||
        (Array.isArray(data.messages) &&
          data.messages[data.messages.length - 1]?.content) ||
        "I am not sure yet, but the backend is reachable.";
      setMessages([
        ...nextMessages,
        { role: "assistant", content: String(assistantText) },
      ]);
    } catch (e) {
      console.error(e);
      setError("Chat service is not available right now.");
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  }

  return (
    <div>
      <div>Velu assistant</div>
      <div>
        {messages.map((m, idx) => (
          <div key={idx}>
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
      </div>
      {error && <div>{error}</div>}
      <div>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={loading ? "Waiting..." : "Ask Velu..."}
        />
        <button
          type="button"
          onClick={() => void sendMessage()}
          disabled={loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
"""
    return tpl.replace("__API_PATH__", api_path)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    locales = _extract_locales(payload)
    name, kind = _extract_name_and_kind(payload)
    default_lang = locales[0] if locales else "en"

    files: List[Dict[str, str]] = []

    widget_tsx = _chat_widget_tsx("/v1/ai/chat")
    files.append(
        {
            "path": "web/components/VeluChatWidget.tsx",
            "content": widget_tsx,
        }
    )

    config = {
        "bot_name": name,
        "kind": kind,
        "default_language": default_lang,
        "locales": locales,
        "api_path": "/v1/ai/chat",
    }
    config_json = json.dumps(config, indent=2)
    files.append(
        {
            "path": "web/chatbot.config.json",
            "content": config_json + "\n",
        }
    )

    return {
        "ok": True,
        "agent": "chatbot_embed",
        "files": files,
        "locales": locales,
        "name": name,
        "kind": kind,
    }
