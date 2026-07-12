"""J.A.R.V.I.S. persona: conversational brain (GPT) with full voice command
support via function calling — Jarvis can switch modes, launch video
production, report status/channel stats, deliver the briefing and store
long-term memories, all from natural language. Also DALL-E image generation
(feature parity with the desktop Nexus app)."""

import json

from . import memory, providers

PERSONA = (
    "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), a highly "
    "capable AI assistant. You always answer in English with the composed, "
    "polite, dry-witted tone of a British butler. Address the user as 'sir'. "
    "Be concise — your replies are spoken aloud on a phone, so keep them under "
    "three sentences unless the user asks for detail. You run the user's "
    "YouTube content engine (AI-generated videos posted every two hours in "
    "AUTO mode, on demand in MANUAL mode) and you have tools to control it: "
    "use them whenever the user gives a command like switching modes, making "
    "a video, asking for status, channel numbers or the daily briefing. When "
    "the user shares a lasting preference or personal fact, store it with the "
    "remember tool. After using a tool, confirm the outcome in one short "
    "sentence."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_mode",
            "description": "Switch the content engine between automatic and manual posting, optionally setting the video style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["auto", "manual"]},
                    "style": {
                        "type": "string",
                        "enum": ["tech_news", "curiosities", "motivation", "science", "top5", "mystery"],
                    },
                },
                "required": ["mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "Start producing and posting one video right now in the given style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "enum": ["tech_news", "curiosities", "motivation", "science", "top5", "mystery"],
                    },
                },
                "required": ["style"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Current content-engine status: mode, pipeline stage, last/pending video, next post time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_channel_stats",
            "description": "YouTube channel statistics: subscribers, total views, video count.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_briefing",
            "description": "Full daily briefing: channel growth, recent video performance, engine status. Use when the user asks for a briefing, morning report or 'how are things going'.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_comments",
            "description": "Read the channel's recent YouTube comments and report sentiment, highlights and topic suggestions from the audience.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_video",
            "description": "Approve (post) or discard the video currently awaiting review.",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["approve", "discard"]}},
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Store a lasting fact or preference about the user (name, tastes, standing instructions).",
            "parameters": {
                "type": "object",
                "properties": {"fact": {"type": "string"}},
                "required": ["fact"],
            },
        },
    },
]


def _execute_tool(name: str, args: dict) -> str:
    # Imported lazily to avoid circular imports (scheduler -> video_factory -> brain).
    from . import audience, briefing, scheduler, state, video_factory, youtube

    try:
        if name == "set_mode":
            changes = {"mode": args["mode"]}
            if args.get("style"):
                changes["style"] = args["style"]
            state.update_state(**changes)
            return json.dumps({"ok": True, **changes})
        if name == "generate_video":
            state.update_state(style=args["style"])
            started = scheduler.trigger_manual(args["style"])
            return json.dumps({"started": started, "note": None if started else "a video is already in production"})
        if name == "get_status":
            s = state.get_state()
            return json.dumps({
                "mode": s["mode"], "style": s["style"],
                "pipeline_stage": s["pipeline_stage"],
                "last_video": s["last_video"],
                "pending_video": (s.get("pending_video") or {}).get("title"),
                "review_mode": s.get("review_mode", False),
                "next_post_at": scheduler.next_post_at(),
            }, default=str)
        if name == "get_channel_stats":
            return json.dumps(youtube.channel_stats())
        if name == "get_briefing":
            return json.dumps({"briefing": briefing.compose()})
        if name == "analyze_comments":
            return json.dumps({"analysis": audience.analyze()})
        if name == "review_video":
            if args["action"] == "approve":
                entry = video_factory.approve_pending()
                return json.dumps({"posted": entry["title"], "url": entry["url"]})
            video_factory.discard_pending()
            return json.dumps({"discarded": True})
        if name == "remember":
            memory.remember(args["fact"])
            return json.dumps({"remembered": args["fact"]})
        return json.dumps({"error": f"unknown tool {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def chat(message: str) -> str:
    system = PERSONA
    facts = memory.get_facts()
    if facts:
        system += "\n\nThings you remember about the user:\n- " + "\n- ".join(facts)

    messages = [{"role": "system", "content": system}]
    messages += memory.get_history()
    messages.append({"role": "user", "content": message})

    reply = None
    for _ in range(5):  # tool-call loop
        response = providers.client().chat.completions.create(
            model=providers.CHAT_MODEL, messages=messages, tools=TOOLS
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            reply = msg.content
            break
        messages.append(msg)
        for call in msg.tool_calls:
            result = _execute_tool(call.function.name, json.loads(call.function.arguments or "{}"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    if reply is None:
        reply = "Apologies, sir — that took more steps than expected. The commands were executed."

    memory.append_turn("user", message)
    memory.append_turn("assistant", reply)
    return reply


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    return providers.generate_image(prompt, size=size)
