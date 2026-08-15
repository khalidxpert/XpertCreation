import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)

BRAND = "XpertAcademy"

_WRAP = """<!DOCTYPE html>
<html><body style="margin:0;padding:24px;background:#F6F7FB;
 font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0D1424">
  <div style="max-width:440px;margin:0 auto;background:#fff;border-radius:16px;
       padding:28px;border:1px solid #E4E8F2">
    <div style="font-size:18px;font-weight:700;letter-spacing:-.02em;margin-bottom:18px">
      {brand}
    </div>
    {body}
    <hr style="border:none;border-top:1px solid #E4E8F2;margin:24px 0">
    <p style="font-size:12px;color:#5A657C;line-height:1.5;margin:0">
      This code expires in {ttl} minutes and can be used once.
      If you did not request it, you can ignore this email &mdash;
      but if it keeps happening, reply and tell us.
    </p>
  </div>
</body></html>"""

_CODE_BOX = """<p style="font-size:14px;line-height:1.5;margin:0 0 18px">{intro}</p>
<div style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:30px;
     font-weight:700;letter-spacing:.16em;text-align:center;padding:16px;
     background:#F6F7FB;border-radius:12px;border:1px solid #E4E8F2">{code}</div>"""


def _from():
    return getattr(settings, "DEFAULT_FROM_EMAIL", "no_reply@xpertcreation.com")


def _send(to_email, subject, intro, code, ttl):
    body_html = _WRAP.format(brand=BRAND, ttl=ttl,
                             body=_CODE_BOX.format(intro=intro, code=code))
    text = "%s\n\n%s\n\nCode: %s\n\nExpires in %d minutes." % (BRAND, intro, code, ttl)

    msg = EmailMultiAlternatives(subject=subject, body=text,
                                 from_email=_from(), to=[to_email])
    msg.attach_alternative(body_html, "text/html")
    try:
        msg.send(fail_silently=False)
        return True
    except Exception:
        # Never leak SMTP errors to the caller: it would tell an attacker
        # whether the address exists. Log it and move on.
        log.exception("Failed sending %s email to %s", subject, to_email)
        return False


def send_verify_code(user, code, ttl):
    return _send(
        user.email,
        "%s: confirm your email" % BRAND,
        "Enter this code to confirm your email address. "
        "Your certificates are issued against it, so it has to be right.",
        code, ttl,
    )


def send_reset_code(user, code, ttl):
    return _send(
        user.email,
        "%s: reset your password" % BRAND,
        "Enter this code to set a new password.",
        code, ttl,
    )


def send_password_changed(user):
    """Sent after any successful password change. This is the tripwire that
    tells a real owner their account was taken over."""
    html = _WRAP.format(
        brand=BRAND, ttl=0,
        body='<p style="font-size:14px;line-height:1.5;margin:0">'
             "Your password was just changed. If this was not you, reply to this "
             "email straight away and we will lock the account.</p>",
    )
    msg = EmailMultiAlternatives(
        subject="%s: your password was changed" % BRAND,
        body="Your password was just changed. If this was not you, reply now.",
        from_email=_from(), to=[user.email],
    )
    msg.attach_alternative(html, "text/html")
    try:
        msg.send(fail_silently=True)
    except Exception:
        log.exception("Failed sending password-changed notice to %s", user.email)
