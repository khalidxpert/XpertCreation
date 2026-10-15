import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)

BRAND = "XpertCreation"

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
  <div style="max-width:560px;margin:18px auto 0;padding:0 4px">
<table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;color:#0D1424;font-size:13px;line-height:1.5;border-collapse:collapse">
  <tr>
    <td style="padding:0 14px 0 0;vertical-align:top;border-right:3px solid #1B4DFF">
      <a href="https://xpertcreation.com" target="_blank"><img src="https://xpertcreation.com/brand/icon-180.png" width="72" height="72" alt="XpertCreation" style="display:block;border:0;border-radius:14px;width:72px;height:72px"></a>
      <a href="https://xpertcreation.com/feed" target="_blank"><img src="https://xpertcreation.com/brand/sig-xpertconnect-96.png?v=2" width="48" height="48" alt="XpertConnect" title="XpertConnect" style="display:block;border:0;width:48px;height:48px;margin:10px auto 0"></a>
      <div style="font-size:10px;font-weight:bold;color:#1B4DFF;text-align:center;margin-top:2px">XpertConnect</div>
      <a href="https://xpertcreation.com/market" target="_blank"><img src="https://xpertcreation.com/brand/sig-freelance-96.png" width="44" height="44" alt="Freelance" title="Freelance marketplace" style="display:block;border:0;width:44px;height:44px;margin:10px auto 0;border-radius:10px"></a>
      <div style="font-size:10px;font-weight:bold;color:#16A34A;text-align:center;margin-top:2px">Freelance</div>
    </td>
    <td style="padding:0 0 0 14px;vertical-align:top">
      <div style="font-size:16px;font-weight:bold;color:#0D1424">Syed Khalid Hussain Shah</div>
      <div style="font-size:13px;color:#1B4DFF;font-weight:bold">Founder &amp; CEO, XpertCreation</div>
      <div style="font-size:12px;color:#5A657C;margin:4px 0 6px;max-width:380px">Free learning, tools, jobs and community for everyone, worldwide &mdash; XpertAcademy courses, XpertConnect networking and everyday tools, all in one place.</div>
      <div style="font-size:12.5px;color:#0D1424">
        &#128222; <a href="https://wa.me/923009462916" target="_blank" style="color:#0D1424;text-decoration:none">+92 300 946 2916</a> (WhatsApp)<br>
        &#9993;&#65039; <a href="mailto:khalid@xpertcreation.com" style="color:#0D1424;text-decoration:none">khalid@xpertcreation.com</a><br>
        &#127760; <a href="https://xpertcreation.com" target="_blank" style="color:#1B4DFF;text-decoration:none;font-weight:bold">xpertcreation.com</a>
        &nbsp;&middot;&nbsp; <a href="https://xpertcreation.com/in/khalidxpert" target="_blank" style="color:#1B4DFF;text-decoration:none">XpertConnect profile</a><br>
        &#128205; <a href="https://share.google/dlldq7AKwKRjijusO" target="_blank" style="color:#1B4DFF;text-decoration:none">Find us on Google</a> (Lahore, Pakistan)
      </div>
      <table cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;border-collapse:separate">
        <tr>
          <td bgcolor="#1877F2" style="background:#1877F2;border-radius:8px;padding:6px 12px">
            <a class="xsb" href="https://www.facebook.com/groups/1202505063279206" target="_blank" style="color:#ffffff;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif"><span style="font-family:Georgia,serif;font-size:14px">f</span>&nbsp; Facebook group</a>
          </td>
          <td width="6" style="width:6px;font-size:0">&nbsp;</td>
          <td bgcolor="#7C3AED" style="background:#7C3AED;border-radius:8px;padding:6px 12px">
            <a class="xsb" href="https://xpertcreation.com/chat-rooms" target="_blank" style="color:#ffffff;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif">#&nbsp; IRC chat rooms</a>
          </td>
          <td width="6" style="width:6px;font-size:0">&nbsp;</td>
          <td bgcolor="#ffffff" style="background:#ffffff;border:2px solid #1B4DFF;border-radius:8px;padding:4px 10px">
            <a class="xsb" href="https://xpertcreation.com/feed" target="_blank" style="color:#1B4DFF;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif"><img src="https://xpertcreation.com/brand/sig-xpertconnect-32.png?v=2" width="18" height="18" alt="" style="border:0;width:18px;height:18px;vertical-align:-4px">&nbsp;XpertConnect</a>
          </td>
        </tr>
      </table>
      <div style="font-size:11px;color:#5A657C;margin-top:5px">IRC: <a href="https://xpertcreation.com/irc" target="_blank" style="color:#5A657C">xpertcreation.com/irc</a> &middot; mIRC: irc.xpertcreation.com, port 6697 (SSL)</div>
    </td>
  </tr>
</table>
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
    text += "\n\n--\nSyed Khalid Hussain Shah\nFounder & CEO, XpertCreation\nxpertcreation.com | +92 300 946 2916 (WhatsApp)\nkhalid@xpertcreation.com"

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
