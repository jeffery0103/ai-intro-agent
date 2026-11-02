"""狀態儲存(設定、模擬帳戶、bot 狀態)。
Render 免費方案的硬碟重開就清空,所以有設定 GIST_ID + GITHUB_TOKEN 時存到私人 Gist;沒有就存本機 state/。
token 只從環境變數讀。"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "state")
GIST = os.environ.get("GIST_ID")
_cache = {}          # 同一個程序內讀過或寫過就用記憶體裡的,不用每次去 GitHub 讀


def _gh(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                          "Accept": "application/vnd.github+json"})
    return json.load(urllib.request.urlopen(req, timeout=20))


def load(name):
    if name in _cache:
        return json.loads(_cache[name])
    obj = _load(name)
    _cache[name] = json.dumps(obj)
    return obj


def _load(name):
    if GIST:
        f = _gh("GET", f"https://api.github.com/gists/{GIST}")["files"].get(name)
        if not f:
            return None
        text = urllib.request.urlopen(f["raw_url"], timeout=20).read().decode() if f.get("truncated") else f["content"]
        return json.loads(text)
    p = os.path.join(LOCAL, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def save(name, obj):
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    _cache[name] = json.dumps(obj)
    if GIST:
        _gh("PATCH", f"https://api.github.com/gists/{GIST}", {"files": {name: {"content": text}}})
        return
    os.makedirs(LOCAL, exist_ok=True)
    open(os.path.join(LOCAL, name), "w", encoding="utf-8").write(text)


def delete(name):
    _cache[name] = "null"
    if GIST:
        _gh("PATCH", f"https://api.github.com/gists/{GIST}", {"files": {name: None}})
    elif os.path.exists(os.path.join(LOCAL, name)):
        os.remove(os.path.join(LOCAL, name))
