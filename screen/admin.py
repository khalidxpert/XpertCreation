from django.contrib import admin
from django.utils.html import format_html

from .models import OfficialLink, TitleReview, WatchItem

HOW_TO = """
<div style="background:#F6F7FB;border:1px solid #E4E8F2;border-radius:10px;padding:12px 16px;line-height:1.7;max-width:760px">
<b>How to add an official link</b>
<ol style="margin:6px 0 0 18px;padding:0">
<li>Open the drama or film on <a href="/shows" target="_blank">xpertcreation.com/shows</a>.</li>
<li>Look at the address. <code>/show/tv-12345</code> means <b>Kind</b> = Drama / series and <b>TMDB id</b> = 12345.
    <code>/show/movie-678</code> means Movie and 678.</li>
<li>On YouTube, open the channel's own playlist for that drama (HUM TV, ARY Digital, Har Pal Geo and so on) and copy its link.</li>
<li>Fill in the drama's name, a label such as <i>All episodes on HUM TV</i>, and paste the link. Save.</li>
<li>Open the drama page again: a green button with your label is now there.</li>
</ol>
<p style="margin:8px 0 0">Only YouTube links are accepted, and only from the channel that owns the drama. Never a copy or another site.</p>
</div>
"""


@admin.register(OfficialLink)
class OfficialLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "tmdb_id", "label", "open_page")
    search_fields = ("title", "url")
    fieldsets = ((None, {"description": HOW_TO,
                         "fields": ("kind", "tmdb_id", "title", "label", "url")}),)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        tips = {"kind": "From the address: /show/tv-... is a drama, /show/movie-... is a film.",
                "tmdb_id": "The number in the address: /show/tv-12345 → 12345.",
                "title": "The drama's name, so you can find this link again.",
                "label": "Shown on the button, e.g. 'All episodes on HUM TV'.",
                "url": "The official YouTube playlist or channel link. Other sites are refused."}
        for name, tip in tips.items():
            if name in form.base_fields:
                form.base_fields[name].help_text = tip
        return form

    @admin.display(description="Check")
    def open_page(self, obj):
        return format_html('<a href="/show/{}-{}" target="_blank">Open page</a>', obj.kind, obj.tmdb_id)


@admin.register(TitleReview)
class TitleReviewAdmin(admin.ModelAdmin):
    list_display = ("kind", "tmdb_id", "user", "stars", "hidden", "updated_at")
    list_filter = ("hidden", "stars", "kind")
    list_editable = ("hidden",)


admin.site.register(WatchItem)
