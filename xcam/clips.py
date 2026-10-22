"""Short video clips (XpertCam) in chats and groups.
Chats already take documents through notifications.chatx.save_file. This lets that same path also take
clips (webm / mp4 / mov, up to 8 MB), checked by their first bytes, and stored with the other chat files."""
import os
import secrets

VIDEO_EXT = {"webm": "video/webm", "mp4": "video/mp4", "mov": "video/quicktime"}
MAX_CLIP = 8 * 1024 * 1024


def _is_clip(ext, head):
    if ext == "webm":
        return head[:4] == b"\x1a\x45\xdf\xa3"
    return head[4:8] == b"ftyp"


def patch():
    try:
        from notifications import chatx
    except Exception:
        return
    orig = chatx.save_file
    if getattr(orig, "_xcam", False):
        return

    def save_file(f, thread_id):
        name = os.path.basename(str(getattr(f, "name", "") or "clip"))[:120]
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in VIDEO_EXT:
            return orig(f, thread_id)
        if f.size > MAX_CLIP:
            raise ValueError("That clip is over 8 MB. Record a shorter one.")
        head = f.read(16)
        f.seek(0)
        if not _is_clip(ext, head):
            raise ValueError("That does not look like a real video clip.")
        rel = "%d/%s.%s" % (thread_id, secrets.token_hex(12), ext)
        full = os.path.join(chatx.FILES_DIR, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        return rel, name, f.size

    save_file._xcam = True
    chatx.save_file = save_file
