#!/usr/bin/env python3
"""Telegram course -> XpertAcademy login (setup_lwe_academy_v1)
XpertCreation side (/var/www/xpertcreation-api): new app "tgacademy" — signed private API for the bot:
   provision (create/find the buyer's account, username = Telegram username, enrol) · link (new sign-in link) ·
   go/<token> (one-time "Start learning" link: signs in and opens the course)
Bot side (/opt/solana-shop): after a paid course -> XpertAcademy login + ▶️ Start learning button; /academy command;
   menu gets 🔄 Swap · 🌉 Bridge · 🎓 XpertAcademy buttons.
Course map (bot id -> academy slug) in /opt/solana-shop/.env ACADEMY_MAP. Shared secret is generated, never printed.
Run:  python3 /root/setup_lwe_academy_v1.py           (checks only)
      python3 /root/setup_lwe_academy_v1.py --apply   (backup, install, restart)
"""
import base64, glob, os, re, secrets, shutil, subprocess, sys, time

FILES = {
    'academy_link.py': 'IiIiVGVsZWdyYW0gcHVyY2hhc2UgLT4gWHBlcnRBY2FkZW15IGFjY291bnQgKyBjb3Vyc2UgYWNjZXNzIChzZXR1cF9sd2VfYWNhZGVteV92MSkuCgpBZnRlciBhIGNvdXJzZSBpcyBwYWlkIGluIHRoZSBib3QsIHRoZSBib3QgYXNrcyBYcGVydENyZWF0aW9uIChzaWduZWQgcmVxdWVzdCwgc2hhcmVkIHNlY3JldCkgdG8gY3JlYXRlIG9yIGZpbmQgdGhlCmJ1eWVyJ3MgWHBlcnRBY2FkZW15IGFjY291bnQgKHVzZXJuYW1lID0gVGVsZWdyYW0gdXNlcm5hbWUpIGFuZCBlbnJvbCB0aGVtLiBUaGUgYnV5ZXIgZ2V0cyB0aGVpciBsb2dpbiBkZXRhaWxzIG9uY2UsCnBsdXMgYSAiU3RhcnQgbGVhcm5pbmciIGJ1dHRvbiB0aGF0IHNpZ25zIHRoZW0gaW4gYW5kIG9wZW5zIHRoZSBjb3Vyc2UuCiIiIgppbXBvcnQgaGFzaGxpYgppbXBvcnQgaG1hYwppbXBvcnQganNvbgppbXBvcnQgbG9nZ2luZwppbXBvcnQgb3MKaW1wb3J0IHRpbWUKCmltcG9ydCBodHRweApmcm9tIHRlbGVncmFtIGltcG9ydCBJbmxpbmVLZXlib2FyZEJ1dHRvbiwgSW5saW5lS2V5Ym9hcmRNYXJrdXAKZnJvbSB0ZWxlZ3JhbS5jb25zdGFudHMgaW1wb3J0IFBhcnNlTW9kZQoKaW1wb3J0IGNvbmZpZyAgIyBub3FhOiBGNDAxICAobG9hZHMgLmVudikKaW1wb3J0IGRiCgpsb2cgPSBsb2dnaW5nLmdldExvZ2dlcigiYWNhZGVteSIpCkFQSSA9IG9zLmdldGVudigiQUNBREVNWV9BUEkiLCAiaHR0cHM6Ly94cGVydGNyZWF0aW9uLmNvbS9hcGkvdGdhY2FkZW15IikucnN0cmlwKCIvIikKU0VDUkVUID0gb3MuZ2V0ZW52KCJBQ0FERU1ZX1NFQ1JFVCIsICIiKS5zdHJpcCgpCiMgYm90IGNvdXJzZV9pZCAtPiBYcGVydEFjYWRlbXkgY291cnNlIHNsdWcKTUFQID0ge30KZm9yIHBhcnQgaW4gb3MuZ2V0ZW52KCJBQ0FERU1ZX01BUCIsICIiKS5yZXBsYWNlKCIgIiwgIiIpLnNwbGl0KCIsIik6CiAgICBpZiAiOiIgaW4gcGFydDoKICAgICAgICBrLCB2ID0gcGFydC5zcGxpdCgiOiIsIDEpCiAgICAgICAgaWYgay5pc2RpZ2l0KCkgYW5kIHY6CiAgICAgICAgICAgIE1BUFtpbnQoayldID0gdgoKCmRlZiBtYXBwZWQoY291cnNlX2lkKSAtPiBib29sOgogICAgcmV0dXJuIGJvb2woU0VDUkVUKSBhbmQgaW50KGNvdXJzZV9pZCkgaW4gTUFQCgoKYXN5bmMgZGVmIF9jYWxsKHBhdGg6IHN0ciwgcGF5bG9hZDogZGljdCkgLT4gZGljdDoKICAgIHBheWxvYWQgPSBkaWN0KHBheWxvYWQsIHRzPWludCh0aW1lLnRpbWUoKSkpCiAgICByYXcgPSBqc29uLmR1bXBzKHBheWxvYWQsIHNlcGFyYXRvcnM9KCIsIiwgIjoiKSwgc29ydF9rZXlzPVRydWUpLmVuY29kZSgpCiAgICBzaWcgPSBobWFjLm5ldyhTRUNSRVQuZW5jb2RlKCksIHJhdywgaGFzaGxpYi5zaGEyNTYpLmhleGRpZ2VzdCgpCiAgICBhc3luYyB3aXRoIGh0dHB4LkFzeW5jQ2xpZW50KHRpbWVvdXQ9MjApIGFzIGM6CiAgICAgICAgciA9IGF3YWl0IGMucG9zdChBUEkgKyBwYXRoLCBjb250ZW50PXJhdywgaGVhZGVycz17IkNvbnRlbnQtVHlwZSI6ICJhcHBsaWNhdGlvbi9qc29uIiwgIlgtVEctU2lnbiI6IHNpZ30pCiAgICBpZiByLnN0YXR1c19jb2RlICE9IDIwMDoKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoImFjYWRlbXkgJXM6ICVzICVzIiAlIChwYXRoLCByLnN0YXR1c19jb2RlLCByLnRleHRbOjIwMF0pKQogICAgcmV0dXJuIHIuanNvbigpCgoKZGVmIF93aG8odGdfaWQ6IGludCkgLT4gZGljdDoKICAgIHUgPSBkYi51c2VyKHRnX2lkKQogICAgcmV0dXJuIHsidGdfaWQiOiBpbnQodGdfaWQpLCAidXNlcm5hbWUiOiAodVsidXNlcm5hbWUiXSBpZiB1IGVsc2UgIiIpIG9yICIiLCAibmFtZSI6ICh1WyJuYW1lIl0gaWYgdSBlbHNlICIiKSBvciAiIn0KCgpkZWYgX2tiKHVybDogc3RyKSAtPiBJbmxpbmVLZXlib2FyZE1hcmt1cDoKICAgIHJldHVybiBJbmxpbmVLZXlib2FyZE1hcmt1cChbW0lubGluZUtleWJvYXJkQnV0dG9uKCLilrbvuI8gU3RhcnQgbGVhcm5pbmciLCB1cmw9dXJsKV0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFtJbmxpbmVLZXlib2FyZEJ1dHRvbigi8J+UkSBOZXcgbG9naW4gbGluayIsIGNhbGxiYWNrX2RhdGE9ImFjYWQ6bG9naW4iKV1dKQoKCmFzeW5jIGRlZiBhZnRlcl9wYWlkKGFwcCwgb3JkZXJfcm93KSAtPiBOb25lOgogICAgIiIiRW5yb2wgdGhlIGJ1eWVyIGluIHRoZSBtYXRjaGluZyBYcGVydEFjYWRlbXkgY291cnNlIGFuZCBzZW5kIHRoZSBsb2dpbi4iIiIKICAgIGlmIG5vdCBtYXBwZWQob3JkZXJfcm93WyJjb3Vyc2VfaWQiXSk6CiAgICAgICAgcmV0dXJuCiAgICBjaGF0ID0gb3JkZXJfcm93WyJ0Z19pZCJdCiAgICB0cnk6CiAgICAgICAgciA9IGF3YWl0IF9jYWxsKCIvcHJvdmlzaW9uIiwgZGljdChfd2hvKGNoYXQpLCBjb3Vyc2U9TUFQW2ludChvcmRlcl9yb3dbImNvdXJzZV9pZCJdKV0sIG9yZGVyPW9yZGVyX3Jvd1sib3JkZXJfaWQiXSkpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGV4YzogICMgbm9xYTogQkxFMDAxCiAgICAgICAgbG9nLndhcm5pbmcoImFjYWRlbXkgcHJvdmlzaW9uIGZhaWwgb3JkZXI9JXM6ICVzIiwgb3JkZXJfcm93WyJvcmRlcl9pZCJdLCBleGMpCiAgICAgICAgYXdhaXQgYXBwLmJvdC5zZW5kX21lc3NhZ2UoY2hhdCwgIuKaoO+4jyBZb3VyIHBheW1lbnQgaXMgY29uZmlybWVkLiBTZXR0aW5nIHVwIHlvdXIgWHBlcnRBY2FkZW15IGFjY2VzcyBmYWlsZWQgZm9yIGEgbW9tZW50IOKAlCAiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInRhcCAvYWNhZGVteSBpbiBhIGZldyBtaW51dGVzLCBvciBjb250YWN0IHN1cHBvcnQuIikKICAgICAgICByZXR1cm4KICAgIGxpbmVzID0gWyLwn46TICpZb3UncmUgZW5yb2xsZWQgaW4gWHBlcnRBY2FkZW15ISoiLCAiIiwgIkNvdXJzZTogKiVzKiIgJSByLmdldCgiY291cnNlX3RpdGxlIiwgIiIpXQogICAgaWYgci5nZXQoInBhc3N3b3JkIik6CiAgICAgICAgbGluZXMgKz0gWyIiLCAiWW91ciBYcGVydEFjYWRlbXkgYWNjb3VudDoiLCAiVXNlcm5hbWU6IGAlc2AiICUgclsidXNlcm5hbWUiXSwgIkxvZ2luIGVtYWlsOiBgJXNgIiAlIHJbImVtYWlsIl0sCiAgICAgICAgICAgICAgICAgICJQYXNzd29yZDogYCVzYCIgJSByWyJwYXNzd29yZCJdLCAiIiwgIl9TYXZlIHRoZXNlLiBZb3UgY2FuIGNoYW5nZSB0aGUgcGFzc3dvcmQgaW4gWHBlcnRDcmVhdGlvbiBzZXR0aW5ncy5fIl0KICAgIGVsc2U6CiAgICAgICAgbGluZXMgKz0gWyIiLCAiSXQncyBhZGRlZCB0byB5b3VyIGFjY291bnQgYCVzYC4iICUgci5nZXQoInVzZXJuYW1lIiwgIiIpXQogICAgbGluZXMgKz0gWyIiLCAiVGFwICpTdGFydCBsZWFybmluZyog4oCUIGl0IHNpZ25zIHlvdSBpbiBhbmQgb3BlbnMgdGhlIGNvdXJzZSAobGluayB3b3JrcyBvbmNlLCBmb3IgNyBkYXlzKS4iXQogICAgYXdhaXQgYXBwLmJvdC5zZW5kX21lc3NhZ2UoY2hhdCwgIlxuIi5qb2luKGxpbmVzKSwgcGFyc2VfbW9kZT1QYXJzZU1vZGUuTUFSS0RPV04sIHJlcGx5X21hcmt1cD1fa2IoclsibG9naW5fdXJsIl0pKQoKCmFzeW5jIGRlZiBzZW5kX2xvZ2luKGFwcCwgdGdfaWQ6IGludCkgLT4gTm9uZToKICAgICIiIkEgZnJlc2ggb25lLXRpbWUgc2lnbi1pbiBsaW5rIChidXR0b24g8J+UkSAvIGNvbW1hbmQgL2FjYWRlbXkpLiIiIgogICAgaWYgbm90IFNFQ1JFVDoKICAgICAgICBhd2FpdCBhcHAuYm90LnNlbmRfbWVzc2FnZSh0Z19pZCwgIlhwZXJ0QWNhZGVteSBsb2dpbiBpcyBub3Qgc2V0IHVwIHlldC4iKQogICAgICAgIHJldHVybgogICAgdHJ5OgogICAgICAgIHIgPSBhd2FpdCBfY2FsbCgiL2xpbmsiLCBfd2hvKHRnX2lkKSkKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXhjOiAgIyBub3FhOiBCTEUwMDEKICAgICAgICBsb2cud2FybmluZygiYWNhZGVteSBsaW5rIGZhaWwgdGc9JXM6ICVzIiwgdGdfaWQsIGV4YykKICAgICAgICBhd2FpdCBhcHAuYm90LnNlbmRfbWVzc2FnZSh0Z19pZCwgIuKaoO+4jyBDb3VsZCBub3QgbWFrZSBhIGxvZ2luIGxpbmsgcmlnaHQgbm93LiBQbGVhc2UgdHJ5IGFnYWluIGluIGEgbWludXRlLiIpCiAgICAgICAgcmV0dXJuCiAgICBpZiBub3Qgci5nZXQoImxvZ2luX3VybCIpOgogICAgICAgIGF3YWl0IGFwcC5ib3Quc2VuZF9tZXNzYWdlKHRnX2lkLCAiWW91IGRvbid0IGhhdmUgYW4gWHBlcnRBY2FkZW15IGFjY291bnQgeWV0IOKAlCBidXkgYSBjb3Vyc2UgYW5kIGl0IGlzIGNyZWF0ZWQgZm9yIHlvdS4iKQogICAgICAgIHJldHVybgogICAgY291cnNlcyA9ICIsICIuam9pbihyLmdldCgiY291cnNlcyIpIG9yIFtdKSBvciAi4oCUIgogICAgYXdhaXQgYXBwLmJvdC5zZW5kX21lc3NhZ2UodGdfaWQsICLwn46TICpYcGVydEFjYWRlbXkqXG5BY2NvdW50OiBgJXNgXG5Zb3VyIGNvdXJzZXM6ICVzXG5cblRhcCBiZWxvdyB0byBzaWduIGluICh3b3JrcyBvbmNlLCBmb3IgNyBkYXlzKS4iICUgKHIuZ2V0KCJ1c2VybmFtZSIsICIiKSwgY291cnNlcyksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwYXJzZV9tb2RlPVBhcnNlTW9kZS5NQVJLRE9XTiwgcmVwbHlfbWFya3VwPV9rYihyWyJsb2dpbl91cmwiXSkpCg==',
    'tgacademy/__init__.py': '',
    'tgacademy/apps.py': 'ZnJvbSBkamFuZ28uYXBwcyBpbXBvcnQgQXBwQ29uZmlnCgoKY2xhc3MgVGdhY2FkZW15Q29uZmlnKEFwcENvbmZpZyk6CiAgICBkZWZhdWx0X2F1dG9fZmllbGQgPSAiZGphbmdvLmRiLm1vZGVscy5CaWdBdXRvRmllbGQiCiAgICBuYW1lID0gInRnYWNhZGVteSIK',
    'tgacademy/models.py': 'IiIiVGVsZWdyYW0gKEBEYW1hQWNhZGVteUJvdCkgYnV5ZXJzIC0+IFhwZXJ0QWNhZGVteSBhY2NvdW50cyBhbmQgY291cnNlIGVucm9sbWVudHMuIiIiCmZyb20gZGphbmdvLmNvbmYgaW1wb3J0IHNldHRpbmdzCmZyb20gZGphbmdvLmRiIGltcG9ydCBtb2RlbHMKZnJvbSBkamFuZ28udXRpbHMgaW1wb3J0IHRpbWV6b25lCgoKY2xhc3MgVGdMaW5rKG1vZGVscy5Nb2RlbCk6CiAgICB1c2VyID0gbW9kZWxzLk9uZVRvT25lRmllbGQoc2V0dGluZ3MuQVVUSF9VU0VSX01PREVMLCBvbl9kZWxldGU9bW9kZWxzLkNBU0NBREUsIHJlbGF0ZWRfbmFtZT0idGdfbGluayIpCiAgICB0Z19pZCA9IG1vZGVscy5CaWdJbnRlZ2VyRmllbGQodW5pcXVlPVRydWUpCiAgICB0Z191c2VybmFtZSA9IG1vZGVscy5DaGFyRmllbGQobWF4X2xlbmd0aD02NCwgYmxhbms9VHJ1ZSwgZGVmYXVsdD0iIikKICAgIGNyZWF0ZWQgPSBtb2RlbHMuRGF0ZVRpbWVGaWVsZChkZWZhdWx0PXRpbWV6b25lLm5vdykKCgpjbGFzcyBFbnJvbGxtZW50KG1vZGVscy5Nb2RlbCk6CiAgICAiIiJBIHBhaWQgY291cnNlIChmcm9tIHRoZSBUZWxlZ3JhbSBib3QpLiBMYXRlciB1c2VkIHRvIHVubG9jayBwYWlkIGNvdXJzZXMuIiIiCiAgICB1c2VyID0gbW9kZWxzLkZvcmVpZ25LZXkoc2V0dGluZ3MuQVVUSF9VU0VSX01PREVMLCBvbl9kZWxldGU9bW9kZWxzLkNBU0NBREUsIHJlbGF0ZWRfbmFtZT0idGdfZW5yb2xsbWVudHMiKQogICAgY291cnNlID0gbW9kZWxzLkZvcmVpZ25LZXkoImFjYWRlbXkuQ291cnNlIiwgb25fZGVsZXRlPW1vZGVscy5DQVNDQURFLCByZWxhdGVkX25hbWU9InRnX2Vucm9sbG1lbnRzIikKICAgIHNvdXJjZSA9IG1vZGVscy5DaGFyRmllbGQobWF4X2xlbmd0aD0yMCwgZGVmYXVsdD0idGVsZWdyYW0iKQogICAgb3JkZXJfaWQgPSBtb2RlbHMuQ2hhckZpZWxkKG1heF9sZW5ndGg9NDAsIHVuaXF1ZT1UcnVlKQogICAgY3JlYXRlZCA9IG1vZGVscy5EYXRlVGltZUZpZWxkKGRlZmF1bHQ9dGltZXpvbmUubm93KQoKICAgIGNsYXNzIE1ldGE6CiAgICAgICAgdW5pcXVlX3RvZ2V0aGVyID0gWygidXNlciIsICJjb3Vyc2UiKV0KCgpjbGFzcyBMb2dpblRpY2tldChtb2RlbHMuTW9kZWwpOgogICAgIiIiT25lLXRpbWUgc2lnbi1pbiBsaW5rIHNlbnQgaW4gVGVsZWdyYW0gKDcgZGF5cykuIiIiCiAgICB1c2VyID0gbW9kZWxzLkZvcmVpZ25LZXkoc2V0dGluZ3MuQVVUSF9VU0VSX01PREVMLCBvbl9kZWxldGU9bW9kZWxzLkNBU0NBREUsIHJlbGF0ZWRfbmFtZT0idGdfdGlja2V0cyIpCiAgICB0b2tlbl9oYXNoID0gbW9kZWxzLkNoYXJGaWVsZChtYXhfbGVuZ3RoPTY0LCB1bmlxdWU9VHJ1ZSkKICAgIG5leHRfdXJsID0gbW9kZWxzLkNoYXJGaWVsZChtYXhfbGVuZ3RoPTIwMCwgZGVmYXVsdD0iL2FjYWRlbXkvIikKICAgIGV4cGlyZXMgPSBtb2RlbHMuRGF0ZVRpbWVGaWVsZCgpCiAgICB1c2VkID0gbW9kZWxzLkRhdGVUaW1lRmllbGQobnVsbD1UcnVlLCBibGFuaz1UcnVlKQo=',
    'tgacademy/urls.py': 'ZnJvbSBkamFuZ28udXJscyBpbXBvcnQgcGF0aAoKZnJvbSAuIGltcG9ydCB2aWV3cwoKdXJscGF0dGVybnMgPSBbCiAgICBwYXRoKCJwcm92aXNpb24iLCB2aWV3cy5wcm92aXNpb24pLAogICAgcGF0aCgibGluayIsIHZpZXdzLmxpbmspLAogICAgcGF0aCgiZ28vPHN0cjp0b2tlbj4iLCB2aWV3cy5nbyksCl0K',
    'tgacademy/views.py': 'IiIiUHJpdmF0ZSBBUEkgZm9yIEBEYW1hQWNhZGVteUJvdCAoc2V0dXBfbHdlX2FjYWRlbXlfdjEpLiBFdmVyeSBib3QgY2FsbCBpcyBzaWduZWQgd2l0aCBUR0FDQURFTVlfU0VDUkVUIChITUFDLVNIQTI1NgpvZiB0aGUgYm9keSwgdGltZXN0YW1wIGluc2lkZSwgNSBtaW51dGVzKS4gL2dvLzx0b2tlbj4gaXMgdGhlIG9uZS10aW1lICJTdGFydCBsZWFybmluZyIgbGluay4iIiIKaW1wb3J0IGhhc2hsaWIKaW1wb3J0IGhtYWMKaW1wb3J0IGpzb24KaW1wb3J0IHJlCmltcG9ydCBzZWNyZXRzCmltcG9ydCBzdHJpbmcKaW1wb3J0IHRpbWUKZnJvbSBkYXRldGltZSBpbXBvcnQgdGltZWRlbHRhCgpmcm9tIGRqYW5nby5jb25mIGltcG9ydCBzZXR0aW5ncwpmcm9tIGRqYW5nby5jb250cmliLmF1dGggaW1wb3J0IGdldF91c2VyX21vZGVsLCBsb2dpbgpmcm9tIGRqYW5nby5kYiBpbXBvcnQgSW50ZWdyaXR5RXJyb3IsIHRyYW5zYWN0aW9uCmZyb20gZGphbmdvLmh0dHAgaW1wb3J0IEh0dHBSZXNwb25zZVJlZGlyZWN0LCBKc29uUmVzcG9uc2UKZnJvbSBkamFuZ28udXRpbHMgaW1wb3J0IHRpbWV6b25lCmZyb20gZGphbmdvLnZpZXdzLmRlY29yYXRvcnMuY3NyZiBpbXBvcnQgY3NyZl9leGVtcHQKCmZyb20gYWNhZGVteS5tb2RlbHMgaW1wb3J0IENvdXJzZQoKZnJvbSAubW9kZWxzIGltcG9ydCBFbnJvbGxtZW50LCBMb2dpblRpY2tldCwgVGdMaW5rCgpVc2VyID0gZ2V0X3VzZXJfbW9kZWwoKQpTSVRFID0gImh0dHBzOi8veHBlcnRjcmVhdGlvbi5jb20iCgoKZGVmIF9lbnYoaywgZD0iIik6CiAgICB0cnk6CiAgICAgICAgZnJvbSB4cGVydGFwaS5zZXR0aW5ncyBpbXBvcnQgZW52CiAgICAgICAgcmV0dXJuIGVudihrLCBkKQogICAgZXhjZXB0IEV4Y2VwdGlvbjogICMgbm9xYTogQkxFMDAxCiAgICAgICAgaW1wb3J0IG9zCiAgICAgICAgcmV0dXJuIG9zLmVudmlyb24uZ2V0KGssIGQpCgoKZGVmIF9lcnIobXNnLCBjb2RlPTQwMCk6CiAgICByZXR1cm4gSnNvblJlc3BvbnNlKHsiZGV0YWlsIjogbXNnfSwgc3RhdHVzPWNvZGUpCgoKZGVmIF9zaWduZWQocmVxdWVzdCk6CiAgICBzZWNyZXQgPSBfZW52KCJUR0FDQURFTVlfU0VDUkVUIiwgIiIpCiAgICBpZiBub3Qgc2VjcmV0IG9yIHJlcXVlc3QubWV0aG9kICE9ICJQT1NUIjoKICAgICAgICByZXR1cm4gTm9uZQogICAgcmF3ID0gcmVxdWVzdC5ib2R5IG9yIGIiIgogICAgd2FudCA9IGhtYWMubmV3KHNlY3JldC5lbmNvZGUoKSwgcmF3LCBoYXNobGliLnNoYTI1NikuaGV4ZGlnZXN0KCkKICAgIGlmIG5vdCBobWFjLmNvbXBhcmVfZGlnZXN0KHdhbnQsIHJlcXVlc3QuaGVhZGVycy5nZXQoIlgtVEctU2lnbiIsICIiKSk6CiAgICAgICAgcmV0dXJuIE5vbmUKICAgIHRyeToKICAgICAgICBkID0ganNvbi5sb2FkcyhyYXcpCiAgICBleGNlcHQgVmFsdWVFcnJvcjoKICAgICAgICByZXR1cm4gTm9uZQogICAgaWYgYWJzKHRpbWUudGltZSgpIC0gaW50KGQuZ2V0KCJ0cyIpIG9yIDApKSA+IDMwMCBvciBub3Qgc3RyKGQuZ2V0KCJ0Z19pZCIsICIiKSkubHN0cmlwKCItIikuaXNkaWdpdCgpOgogICAgICAgIHJldHVybiBOb25lCiAgICByZXR1cm4gZAoKCmRlZiBfY291cnNlX3VybChzbHVnKToKICAgIHJldHVybiBfZW52KCJUR0FDQURFTVlfQ09VUlNFX1VSTCIsICIvYWNhZGVteS8/Y291cnNlPXtzbHVnfSIpLnJlcGxhY2UoIntzbHVnfSIsIHNsdWcpCgoKZGVmIF90aWNrZXQodXNlciwgbmV4dF91cmwpOgogICAgdG9rID0gc2VjcmV0cy50b2tlbl91cmxzYWZlKDI0KQogICAgTG9naW5UaWNrZXQub2JqZWN0cy5maWx0ZXIodXNlcj11c2VyLCBleHBpcmVzX19sdD10aW1lem9uZS5ub3coKSkuZGVsZXRlKCkKICAgIExvZ2luVGlja2V0Lm9iamVjdHMuY3JlYXRlKHVzZXI9dXNlciwgdG9rZW5faGFzaD1oYXNobGliLnNoYTI1Nih0b2suZW5jb2RlKCkpLmhleGRpZ2VzdCgpLCBuZXh0X3VybD1uZXh0X3VybFs6MjAwXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGV4cGlyZXM9dGltZXpvbmUubm93KCkgKyB0aW1lZGVsdGEoZGF5cz03KSkKICAgIHJldHVybiBTSVRFICsgIi9hcGkvdGdhY2FkZW15L2dvLyIgKyB0b2sKCgpkZWYgX2ZyZWVfdXNlcm5hbWUod2FudCwgdGdfaWQpOgogICAgYmFzZSA9IHJlLnN1YihyIlteYS16MC05X10iLCAiIiwgKHdhbnQgb3IgIiIpLmxvd2VyKCkpWzoyOF0KICAgIGZvciBjYW5kIGluIChbYmFzZV0gaWYgbGVuKGJhc2UpID49IDMgZWxzZSBbXSkgKyBbKGJhc2Ugb3IgImRhbWEiKSArICJfdGciLCAidGclZCIgJSB0Z19pZF06CiAgICAgICAgaWYgbm90IFVzZXIub2JqZWN0cy5maWx0ZXIodXNlcm5hbWVfX2lleGFjdD1jYW5kKS5leGlzdHMoKToKICAgICAgICAgICAgcmV0dXJuIGNhbmQKICAgIHJldHVybiAidGclZF8lcyIgJSAodGdfaWQsIHNlY3JldHMudG9rZW5faGV4KDIpKQoKCmRlZiBfdXNlcl9mb3IoZCwgY3JlYXRlKToKICAgICIiIih1c2VyLCBwYXNzd29yZC1pZi1uZXcpLiBGaW5kcyB0aGUgYWNjb3VudCBsaW5rZWQgdG8gdGhpcyBUZWxlZ3JhbSBpZCwgb3IgbWFrZXMgb25lLiIiIgogICAgdGdfaWQgPSBpbnQoZFsidGdfaWQiXSkKICAgIGxpbmsgPSBUZ0xpbmsub2JqZWN0cy5zZWxlY3RfcmVsYXRlZCgidXNlciIpLmZpbHRlcih0Z19pZD10Z19pZCkuZmlyc3QoKQogICAgaWYgbGluazoKICAgICAgICBpZiBkLmdldCgidXNlcm5hbWUiKSBhbmQgbGluay50Z191c2VybmFtZSAhPSBkWyJ1c2VybmFtZSJdOgogICAgICAgICAgICBUZ0xpbmsub2JqZWN0cy5maWx0ZXIocGs9bGluay5waykudXBkYXRlKHRnX3VzZXJuYW1lPXN0cihkWyJ1c2VybmFtZSJdKVs6NjRdKQogICAgICAgIHJldHVybiBsaW5rLnVzZXIsICIiCiAgICBpZiBub3QgY3JlYXRlOgogICAgICAgIHJldHVybiBOb25lLCAiIgogICAgcHcgPSAiIi5qb2luKHNlY3JldHMuY2hvaWNlKHN0cmluZy5hc2NpaV9sZXR0ZXJzICsgc3RyaW5nLmRpZ2l0cykgZm9yIF8gaW4gcmFuZ2UoMTApKQogICAgd2l0aCB0cmFuc2FjdGlvbi5hdG9taWMoKToKICAgICAgICB1c2VyID0gVXNlci5vYmplY3RzLmNyZWF0ZV91c2VyKGVtYWlsPSJ0ZyVkQHVzZXJzLnRlbGVncmFtLmludmFsaWQiICUgdGdfaWQsIHBhc3N3b3JkPXB3LAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZnVsbF9uYW1lPXN0cihkLmdldCgibmFtZSIpIG9yIGQuZ2V0KCJ1c2VybmFtZSIpIG9yICJEYW1hIGxlYXJuZXIiKVs6MTAwXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHVzZXJuYW1lPV9mcmVlX3VzZXJuYW1lKGQuZ2V0KCJ1c2VybmFtZSIpLCB0Z19pZCkpCiAgICAgICAgZmllbGRzID0gW10KICAgICAgICBmb3IgZiwgdiBpbiAoKCJpc19lbWFpbF92ZXJpZmllZCIsIFRydWUpLCAoInNpZ251cF9jb3VudHJ5IiwgIiIpKToKICAgICAgICAgICAgaWYgaGFzYXR0cih1c2VyLCBmKToKICAgICAgICAgICAgICAgIHNldGF0dHIodXNlciwgZiwgdik7IGZpZWxkcy5hcHBlbmQoZikKICAgICAgICBpZiBmaWVsZHM6CiAgICAgICAgICAgIHVzZXIuc2F2ZSh1cGRhdGVfZmllbGRzPWZpZWxkcykKICAgICAgICBUZ0xpbmsub2JqZWN0cy5jcmVhdGUodXNlcj11c2VyLCB0Z19pZD10Z19pZCwgdGdfdXNlcm5hbWU9c3RyKGQuZ2V0KCJ1c2VybmFtZSIpIG9yICIiKVs6NjRdKQogICAgcmV0dXJuIHVzZXIsIHB3CgoKQGNzcmZfZXhlbXB0CmRlZiBwcm92aXNpb24ocmVxdWVzdCk6CiAgICBkID0gX3NpZ25lZChyZXF1ZXN0KQogICAgaWYgZCBpcyBOb25lOgogICAgICAgIHJldHVybiBfZXJyKCJOb3QgYWxsb3dlZC4iLCA0MDMpCiAgICBjb3Vyc2UgPSBDb3Vyc2Uub2JqZWN0cy5maWx0ZXIoc2x1Zz1zdHIoZC5nZXQoImNvdXJzZSIpIG9yICIiKSkuZmlyc3QoKQogICAgaWYgbm90IGNvdXJzZToKICAgICAgICByZXR1cm4gX2VycigiVW5rbm93biBjb3Vyc2UuIiwgNDA0KQogICAgb3JkZXIgPSBzdHIoZC5nZXQoIm9yZGVyIikgb3IgIiIpWzo0MF0KICAgIGlmIG5vdCBvcmRlcjoKICAgICAgICByZXR1cm4gX2VycigiT3JkZXIgbWlzc2luZy4iKQogICAgdHJ5OgogICAgICAgIHVzZXIsIHB3ID0gX3VzZXJfZm9yKGQsIFRydWUpCiAgICBleGNlcHQgSW50ZWdyaXR5RXJyb3I6CiAgICAgICAgdXNlciwgcHcgPSBfdXNlcl9mb3IoZCwgRmFsc2UpCiAgICBpZiBub3QgdXNlcjoKICAgICAgICByZXR1cm4gX2VycigiQ291bGQgbm90IGNyZWF0ZSB0aGUgYWNjb3VudC4iLCA1MDApCiAgICBpZiBub3QgRW5yb2xsbWVudC5vYmplY3RzLmZpbHRlcihvcmRlcl9pZD1vcmRlcikuZXhpc3RzKCk6CiAgICAgICAgRW5yb2xsbWVudC5vYmplY3RzLmdldF9vcl9jcmVhdGUodXNlcj11c2VyLCBjb3Vyc2U9Y291cnNlLCBkZWZhdWx0cz17Im9yZGVyX2lkIjogb3JkZXJ9KQogICAgcmV0dXJuIEpzb25SZXNwb25zZSh7InVzZXJuYW1lIjogdXNlci51c2VybmFtZSBvciAiIiwgImVtYWlsIjogdXNlci5lbWFpbCBpZiBwdyBlbHNlICIiLCAicGFzc3dvcmQiOiBwdywKICAgICAgICAgICAgICAgICAgICAgICAgICJjb3Vyc2VfdGl0bGUiOiBjb3Vyc2UudGl0bGUsICJsb2dpbl91cmwiOiBfdGlja2V0KHVzZXIsIF9jb3Vyc2VfdXJsKGNvdXJzZS5zbHVnKSl9KQoKCkBjc3JmX2V4ZW1wdApkZWYgbGluayhyZXF1ZXN0KToKICAgIGQgPSBfc2lnbmVkKHJlcXVlc3QpCiAgICBpZiBkIGlzIE5vbmU6CiAgICAgICAgcmV0dXJuIF9lcnIoIk5vdCBhbGxvd2VkLiIsIDQwMykKICAgIHVzZXIsIF8gPSBfdXNlcl9mb3IoZCwgRmFsc2UpCiAgICBpZiBub3QgdXNlcjoKICAgICAgICByZXR1cm4gSnNvblJlc3BvbnNlKHsibG9naW5fdXJsIjogIiJ9KQogICAgY291cnNlcyA9IGxpc3QoRW5yb2xsbWVudC5vYmplY3RzLmZpbHRlcih1c2VyPXVzZXIpLnNlbGVjdF9yZWxhdGVkKCJjb3Vyc2UiKS52YWx1ZXNfbGlzdCgiY291cnNlX190aXRsZSIsIGZsYXQ9VHJ1ZSkpCiAgICBmaXJzdCA9IEVucm9sbG1lbnQub2JqZWN0cy5maWx0ZXIodXNlcj11c2VyKS5zZWxlY3RfcmVsYXRlZCgiY291cnNlIikub3JkZXJfYnkoIi1jcmVhdGVkIikuZmlyc3QoKQogICAgcmV0dXJuIEpzb25SZXNwb25zZSh7InVzZXJuYW1lIjogdXNlci51c2VybmFtZSBvciAiIiwgImNvdXJzZXMiOiBjb3Vyc2VzLAogICAgICAgICAgICAgICAgICAgICAgICAgImxvZ2luX3VybCI6IF90aWNrZXQodXNlciwgX2NvdXJzZV91cmwoZmlyc3QuY291cnNlLnNsdWcpIGlmIGZpcnN0IGVsc2UgIi9hY2FkZW15LyIpfSkKCgpkZWYgZ28ocmVxdWVzdCwgdG9rZW4pOgogICAgdCA9IExvZ2luVGlja2V0Lm9iamVjdHMuc2VsZWN0X3JlbGF0ZWQoInVzZXIiKS5maWx0ZXIodG9rZW5faGFzaD1oYXNobGliLnNoYTI1Nih0b2tlbi5lbmNvZGUoKSkuaGV4ZGlnZXN0KCkpLmZpcnN0KCkKICAgIGlmIG5vdCB0IG9yIHQudXNlZCBvciB0LmV4cGlyZXMgPCB0aW1lem9uZS5ub3coKSBvciBnZXRhdHRyKHQudXNlciwgImlzX2Jsb2NrZWQiLCBGYWxzZSkgb3Igbm90IHQudXNlci5pc19hY3RpdmU6CiAgICAgICAgcmV0dXJuIEh0dHBSZXNwb25zZVJlZGlyZWN0KCIvbG9naW4/dGc9ZXhwaXJlZCIpCiAgICBMb2dpblRpY2tldC5vYmplY3RzLmZpbHRlcihwaz10LnBrLCB1c2VkX19pc251bGw9VHJ1ZSkudXBkYXRlKHVzZWQ9dGltZXpvbmUubm93KCkpCiAgICBsb2dpbihyZXF1ZXN0LCB0LnVzZXIsIGJhY2tlbmQ9ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIikKICAgIHJlcXVlc3Quc2Vzc2lvbi5jeWNsZV9rZXkoKQogICAgbnh0ID0gdC5uZXh0X3VybCBpZiB0Lm5leHRfdXJsLnN0YXJ0c3dpdGgoIi8iKSBhbmQgbm90IHQubmV4dF91cmwuc3RhcnRzd2l0aCgiLy8iKSBlbHNlICIvYWNhZGVteS8iCiAgICByZXR1cm4gSHR0cFJlc3BvbnNlUmVkaXJlY3Qobnh0KQo=',
    'tgacademy/migrations/__init__.py': '',
    'tgacademy/migrations/0001_initial.py': 'aW1wb3J0IGRqYW5nby5kYi5tb2RlbHMuZGVsZXRpb24KaW1wb3J0IGRqYW5nby51dGlscy50aW1lem9uZQpmcm9tIGRqYW5nby5jb25mIGltcG9ydCBzZXR0aW5ncwpmcm9tIGRqYW5nby5kYiBpbXBvcnQgbWlncmF0aW9ucywgbW9kZWxzCgoKY2xhc3MgTWlncmF0aW9uKG1pZ3JhdGlvbnMuTWlncmF0aW9uKToKICAgIGluaXRpYWwgPSBUcnVlCiAgICBkZXBlbmRlbmNpZXMgPSBbbWlncmF0aW9ucy5zd2FwcGFibGVfZGVwZW5kZW5jeShzZXR0aW5ncy5BVVRIX1VTRVJfTU9ERUwpLCAoImFjYWRlbXkiLCAiX19maXJzdF9fIildCiAgICBvcGVyYXRpb25zID0gWwogICAgICAgIG1pZ3JhdGlvbnMuQ3JlYXRlTW9kZWwobmFtZT0iVGdMaW5rIiwgZmllbGRzPVsKICAgICAgICAgICAgKCJpZCIsIG1vZGVscy5CaWdBdXRvRmllbGQoYXV0b19jcmVhdGVkPVRydWUsIHByaW1hcnlfa2V5PVRydWUsIHNlcmlhbGl6ZT1GYWxzZSwgdmVyYm9zZV9uYW1lPSJJRCIpKSwKICAgICAgICAgICAgKCJ0Z19pZCIsIG1vZGVscy5CaWdJbnRlZ2VyRmllbGQodW5pcXVlPVRydWUpKSwKICAgICAgICAgICAgKCJ0Z191c2VybmFtZSIsIG1vZGVscy5DaGFyRmllbGQoYmxhbms9VHJ1ZSwgZGVmYXVsdD0iIiwgbWF4X2xlbmd0aD02NCkpLAogICAgICAgICAgICAoImNyZWF0ZWQiLCBtb2RlbHMuRGF0ZVRpbWVGaWVsZChkZWZhdWx0PWRqYW5nby51dGlscy50aW1lem9uZS5ub3cpKSwKICAgICAgICAgICAgKCJ1c2VyIiwgbW9kZWxzLk9uZVRvT25lRmllbGQob25fZGVsZXRlPWRqYW5nby5kYi5tb2RlbHMuZGVsZXRpb24uQ0FTQ0FERSwgcmVsYXRlZF9uYW1lPSJ0Z19saW5rIiwgdG89c2V0dGluZ3MuQVVUSF9VU0VSX01PREVMKSksCiAgICAgICAgXSksCiAgICAgICAgbWlncmF0aW9ucy5DcmVhdGVNb2RlbChuYW1lPSJMb2dpblRpY2tldCIsIGZpZWxkcz1bCiAgICAgICAgICAgICgiaWQiLCBtb2RlbHMuQmlnQXV0b0ZpZWxkKGF1dG9fY3JlYXRlZD1UcnVlLCBwcmltYXJ5X2tleT1UcnVlLCBzZXJpYWxpemU9RmFsc2UsIHZlcmJvc2VfbmFtZT0iSUQiKSksCiAgICAgICAgICAgICgidG9rZW5faGFzaCIsIG1vZGVscy5DaGFyRmllbGQobWF4X2xlbmd0aD02NCwgdW5pcXVlPVRydWUpKSwKICAgICAgICAgICAgKCJuZXh0X3VybCIsIG1vZGVscy5DaGFyRmllbGQoZGVmYXVsdD0iL2FjYWRlbXkvIiwgbWF4X2xlbmd0aD0yMDApKSwKICAgICAgICAgICAgKCJleHBpcmVzIiwgbW9kZWxzLkRhdGVUaW1lRmllbGQoKSksCiAgICAgICAgICAgICgidXNlZCIsIG1vZGVscy5EYXRlVGltZUZpZWxkKGJsYW5rPVRydWUsIG51bGw9VHJ1ZSkpLAogICAgICAgICAgICAoInVzZXIiLCBtb2RlbHMuRm9yZWlnbktleShvbl9kZWxldGU9ZGphbmdvLmRiLm1vZGVscy5kZWxldGlvbi5DQVNDQURFLCByZWxhdGVkX25hbWU9InRnX3RpY2tldHMiLCB0bz1zZXR0aW5ncy5BVVRIX1VTRVJfTU9ERUwpKSwKICAgICAgICBdKSwKICAgICAgICBtaWdyYXRpb25zLkNyZWF0ZU1vZGVsKG5hbWU9IkVucm9sbG1lbnQiLCBmaWVsZHM9WwogICAgICAgICAgICAoImlkIiwgbW9kZWxzLkJpZ0F1dG9GaWVsZChhdXRvX2NyZWF0ZWQ9VHJ1ZSwgcHJpbWFyeV9rZXk9VHJ1ZSwgc2VyaWFsaXplPUZhbHNlLCB2ZXJib3NlX25hbWU9IklEIikpLAogICAgICAgICAgICAoInNvdXJjZSIsIG1vZGVscy5DaGFyRmllbGQoZGVmYXVsdD0idGVsZWdyYW0iLCBtYXhfbGVuZ3RoPTIwKSksCiAgICAgICAgICAgICgib3JkZXJfaWQiLCBtb2RlbHMuQ2hhckZpZWxkKG1heF9sZW5ndGg9NDAsIHVuaXF1ZT1UcnVlKSksCiAgICAgICAgICAgICgiY3JlYXRlZCIsIG1vZGVscy5EYXRlVGltZUZpZWxkKGRlZmF1bHQ9ZGphbmdvLnV0aWxzLnRpbWV6b25lLm5vdykpLAogICAgICAgICAgICAoImNvdXJzZSIsIG1vZGVscy5Gb3JlaWduS2V5KG9uX2RlbGV0ZT1kamFuZ28uZGIubW9kZWxzLmRlbGV0aW9uLkNBU0NBREUsIHJlbGF0ZWRfbmFtZT0idGdfZW5yb2xsbWVudHMiLCB0bz0iYWNhZGVteS5jb3Vyc2UiKSksCiAgICAgICAgICAgICgidXNlciIsIG1vZGVscy5Gb3JlaWduS2V5KG9uX2RlbGV0ZT1kamFuZ28uZGIubW9kZWxzLmRlbGV0aW9uLkNBU0NBREUsIHJlbGF0ZWRfbmFtZT0idGdfZW5yb2xsbWVudHMiLCB0bz1zZXR0aW5ncy5BVVRIX1VTRVJfTU9ERUwpKSwKICAgICAgICBdLCBvcHRpb25zPXsidW5pcXVlX3RvZ2V0aGVyIjogeygidXNlciIsICJjb3Vyc2UiKX19KSwKICAgIF0K',
}
XC = "/var/www/xpertcreation-api"
XC_LAND = "/var/www/xpertcreation-landing"
LWE = "/opt/solana-shop"
MAP = "1:excel,2:word,3:digital-marketing,4:digital-marketing,5:freelancing,6:ai-tools"
APPLY = "--apply" in sys.argv
TS = time.strftime("%Y%m%d_%H%M%S")
BK = "/root/backups/lwe_academy_%s" % TS


def die(m):
    print("❌ " + m); sys.exit(1)


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write_keep(p, s, mode=None):
    st = os.stat(p)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(s)
    os.chmod(tmp, mode if mode is not None else st.st_mode & 0o7777)
    os.chown(tmp, st.st_uid, st.st_gid)
    os.replace(tmp, p)


def write_like(p, data, like):
    """New file owned like `like` (a folder or file)."""
    st = os.stat(like)
    with open(p, "wb") as f:
        f.write(data)
    os.chmod(p, 0o644)
    os.chown(p, st.st_uid, st.st_gid)


def env_get(path, k):
    m = re.search(r"(?m)^%s=(.*)$" % re.escape(k), read(path)) if os.path.exists(path) else None
    return m.group(1).strip().strip('"').strip("'") if m else ""


def env_set(s, k, v):
    if re.search(r"(?m)^%s=" % re.escape(k), s):
        return re.sub(r"(?m)^%s=.*$" % re.escape(k), lambda _m: "%s=%s" % (k, v), s)
    return s.rstrip("\n") + "\n%s=%s\n" % (k, v)


def patch(s, old, new, name, where):
    if new in s:
        return s
    if s.count(old) != 1:
        die("%s: '%s' code not found (file differs). Nothing was changed." % (where, name))
    return s.replace(old, new)


def course_url():
    """How the academy page opens one course (looked up in its own files)."""
    for f in glob.glob(XC_LAND + "/academy*/**/*.*", recursive=True) + glob.glob(XC_LAND + "/academy*.html"):
        if not f.endswith((".html", ".js")):
            continue
        try:
            t = read(f)
        except Exception:
            continue
        m = re.search(r"""searchParams\.get\(\s*["'](course|c|slug)["']\s*\)|URLSearchParams\([^)]*\)\.get\(\s*["'](course|c|slug)["']""", t)
        if m:
            return "/academy/?%s={slug}" % (m.group(1) or m.group(2))
        if re.search(r"location\.hash[^;]{0,80}(course|slug)", t):
            return "/academy/#{slug}"
    return "/academy/"


# ---------------- bot.py patches ----------------
B = [
    ("import", "import admin_panel\n", "import academy_link\nimport admin_panel\n"),
    ("deliver", '''        else:
            await app.bot.send_message(chat_id, "⚠️ No PDF is attached to this course yet.")
        db.mark_delivered(order_row["order_id"])''', '''        elif not academy_link.mapped(order_row["course_id"]):
            await app.bot.send_message(chat_id, "⚠️ No PDF is attached to this course yet.")
        db.mark_delivered(order_row["order_id"])
        await academy_link.after_paid(app, order_row)'''),
    ("callback", '''    if data.startswith("buy:"):''', '''    if data == "acad:login":
        await academy_link.send_login(ctx.application, u.id)
        return

    if data.startswith("buy:"):'''),
    ("start acad", '''    if arg == "s":
        await cmd_support(update, ctx)
        return
''', '''    if arg == "s":
        await cmd_support(update, ctx)
        return
    if arg == "acad":
        await academy_link.send_login(ctx.application, u.id)
        return
'''),
    ("/academy", '''    app.add_handler(CommandHandler("support", cmd_support))''', '''    app.add_handler(CommandHandler("support", cmd_support))
    app.add_handler(CommandHandler("academy", lambda up, cx: academy_link.send_login(cx.application, up.effective_user.id)))'''),
    ("menu", '''            [
                InlineKeyboardButton("❓ Help", callback_data="menu:help"),''', '''            [
                InlineKeyboardButton("🔄 Swap SCANAI", url="https://verse.damaacademy.com/#swap"),
                InlineKeyboardButton("🌉 Bridge", url="https://verse.damaacademy.com/bridge"),
            ],
            [InlineKeyboardButton("🎓 XpertAcademy login", callback_data="acad:login")],
            [
                InlineKeyboardButton("❓ Help", callback_data="menu:help"),'''),
]


def xc_service():
    for u in glob.glob("/etc/systemd/system/*.service"):
        t = read(u)
        if XC in t and "gunicorn" in t:
            return os.path.basename(u)[:-8]
    return ""


def main():
    if os.geteuid() != 0:
        die("Run as root.")
    xpy = next((p for p in (XC + "/venv/bin/python", XC + "/.venv/bin/python") if os.path.exists(p)), "")
    for p in (XC + "/manage.py", XC + "/xpertapi/settings.py", XC + "/xpertapi/urls.py", XC + "/academy/models.py", XC + "/.env",
              LWE + "/bot.py", LWE + "/.env", LWE + "/venv/bin/python"):
        if not os.path.exists(p):
            die(p + " not found.")
    if not xpy:
        die("XpertCreation venv not found.")
    svc = xc_service()
    bot = read(LWE + "/bot.py")
    nb = bot
    for name, old, new in B:
        nb = patch(nb, old, new, name, "bot.py")
    url = env_get(XC + "/.env", "TGACADEMY_COURSE_URL") or course_url()
    print("Checks OK")
    print("   XpertCreation: %s  (service %s)" % (XC, svc or "?"))
    print("   course link:   %s" % url)
    print("   course map:    %s" % (env_get(LWE + "/.env", "ACADEMY_MAP") or MAP))
    if not APPLY:
        print("Nothing changed. To install:  python3 /root/setup_lwe_academy_v1.py --apply")
        return

    os.makedirs(BK, mode=0o700, exist_ok=True)
    for p in (XC + "/xpertapi/settings.py", XC + "/xpertapi/urls.py", XC + "/.env", LWE + "/bot.py", LWE + "/.env"):
        dst = BK + "/" + p.strip("/").replace("/", "__")
        shutil.copy2(p, dst); os.chmod(dst, 0o600)
    print("✅ Backup: " + BK)

    def restore(msg):
        for p in (XC + "/xpertapi/settings.py", XC + "/xpertapi/urls.py", LWE + "/bot.py"):
            shutil.copy2(BK + "/" + p.strip("/").replace("/", "__"), p)
        if svc:
            sh("systemctl", "restart", svc)
        sh("systemctl", "restart", "solana-shop")
        die(msg + " — restored the backup.")

    # 1. XpertCreation app
    app_dir = XC + "/tgacademy"
    os.makedirs(app_dir + "/migrations", exist_ok=True)
    st = os.stat(XC + "/academy")
    for d in (app_dir, app_dir + "/migrations"):
        os.chown(d, st.st_uid, st.st_gid)
    for name, b64 in FILES.items():
        if name.startswith("tgacademy/"):
            write_like(XC + "/" + name, base64.b64decode(b64), XC + "/academy/models.py")
    s = read(XC + "/xpertapi/settings.py")
    if '"tgacademy"' not in s:
        write_keep(XC + "/xpertapi/settings.py", s.rstrip("\n") + '\nINSTALLED_APPS += ["tgacademy"]  # setup_lwe_academy_v1\n')
    u = read(XC + "/xpertapi/urls.py")
    if "tgacademy.urls" not in u:
        write_keep(XC + "/xpertapi/urls.py", u.rstrip("\n") + '\nfrom django.urls import include as _tg_inc, path as _tg_path  # setup_lwe_academy_v1\n'
                   'urlpatterns += [_tg_path("api/tgacademy/", _tg_inc("tgacademy.urls"))]\n')
    secret = env_get(XC + "/.env", "TGACADEMY_SECRET") or env_get(LWE + "/.env", "ACADEMY_SECRET") or secrets.token_hex(32)
    e = read(XC + "/.env")
    e = env_set(env_set(e, "TGACADEMY_SECRET", secret), "TGACADEMY_COURSE_URL", url)
    write_keep(XC + "/.env", e)
    r = sh(xpy, "manage.py", "check", cwd=XC)
    if r.returncode:
        restore("XpertCreation check failed:\n" + (r.stderr or r.stdout)[-600:])
    r = sh(xpy, "manage.py", "migrate", "tgacademy", "--noinput", cwd=XC)
    if r.returncode:
        restore("migrate failed:\n" + (r.stderr or r.stdout)[-600:])
    if svc:
        sh("systemctl", "restart", svc)
    print("✅ XpertCreation: tgacademy installed, migrated, %s restarted" % (svc or "(service not found — restart it)"))

    # 2. bot
    write_like(LWE + "/academy_link.py", base64.b64decode(FILES["academy_link.py"]), LWE + "/bot.py")
    os.chmod(LWE + "/academy_link.py", 0o640)
    write_keep(LWE + "/bot.py", nb)
    le = read(LWE + "/.env")
    le = env_set(le, "ACADEMY_SECRET", secret)
    le = env_set(le, "ACADEMY_API", "https://xpertcreation.com/api/tgacademy")
    if not env_get(LWE + "/.env", "ACADEMY_MAP"):
        le = env_set(le, "ACADEMY_MAP", MAP)
    write_keep(LWE + "/.env", le, 0o600)
    r = sh(LWE + "/venv/bin/python", "-m", "py_compile", LWE + "/bot.py", LWE + "/academy_link.py")
    if r.returncode:
        restore("bot.py compile failed:\n" + r.stderr[-500:])
    sh("systemctl", "restart", "solana-shop")
    time.sleep(5)
    print("✅ bot: academy login after payment, /academy, Swap · Bridge · XpertAcademy buttons")

    for s2 in ([svc] if svc else []) + ["solana-shop"]:
        print("   %-22s %s" % (s2, sh("systemctl", "is-active", s2).stdout.strip()))
    t = sh("curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST", "-k", "--resolve", "xpertcreation.com:443:127.0.0.1",
           "https://xpertcreation.com/api/tgacademy/link")
    print("   academy API answers   %s  (403 = working and locked to the bot)" % (t.stdout or "?"))
    print("\nDone. Test: buy a course in @DamaAcademyBot, or send /academy after buying.")


if __name__ == "__main__":
    main()
