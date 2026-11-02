"""Gemini REST API 呼叫。金鑰只從環境變數 GEMINI_API_KEY 讀,不寫進任何檔案。"""
import json, os, time, urllib.request, urllib.error


def _once(model, prompt, system, temperature, thinking, timeout=90):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if thinking:
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": thinking}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    t = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.read().decode()[:300], "sec": round(time.time() - t, 1)}
    except Exception as e:
        return {"error": type(e).__name__, "msg": str(e)[:200], "sec": round(time.time() - t, 1)}
    parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    u = d.get("usageMetadata", {})
    return {"text": "".join(p.get("text", "") for p in parts), "sec": round(time.time() - t, 1),
            "in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"),
            "think": u.get("thoughtsTokenCount"), "model": d.get("modelVersion")}


def call(models, prompt, system=None, temperature=0.2, thinking=None, tries=3, log=None, timeout=90):
    """依序嘗試 models;每個模型遇到 5xx/逾時重試 tries 次(429 直接換),都失敗才換下一個(代打)。
    log 是 list 時,每次嘗試都記一筆,給 Tracing 用。"""
    total = 0.0
    for m in models:
        for i in range(tries):
            r = _once(m, prompt, system, temperature, thinking, timeout)
            total += r["sec"]
            if log is not None:
                log.append({"model": m, "try": i + 1, "sec": r["sec"], "error": r.get("error")})
            if "text" in r:
                r["sec_total"] = round(total, 1)
                r["asked"] = m
                return r
            if r["error"] == 400 and thinking:      # 模型不支援 thinkingLevel 就關掉再試
                thinking = None
                continue
            if r["error"] not in (500, 503, "TimeoutError", "URLError", "timeout"):
                break                                # 429(額度用完)和其他錯誤重試也沒用,直接換模型
            time.sleep(2 * (i + 1))
    return {"error": "all_failed", "sec_total": round(total, 1)}


def parse_json(text):
    """從模型回覆取出 JSON(容許外面包 ```json)。"""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1].rsplit("```", 1)[0]
    a, b = s.find("{"), s.rfind("}")
    return json.loads(s[a:b + 1])
