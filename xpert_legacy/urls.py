from django.urls import path

from . import pages, views

app_name = "xpert_legacy"

urlpatterns = [
    # --- public pages (SEO landing pages) ---
    path("tools/faraid-calculator/", pages.faraid_page, name="faraid_page"),
    path("legal-documents/", pages.documents_page, name="documents_page"),

    # --- JSON API ---
    path("api/faraid/", views.faraid_api, name="faraid_api"),
    path("api/legal/documents/", views.documents_api, name="legal_documents"),
    path("api/legal/render/", views.render_document_api, name="legal_render"),
    path("api/legal/pdf/<str:reference_no>/", views.document_pdf, name="legal_pdf"),
]
