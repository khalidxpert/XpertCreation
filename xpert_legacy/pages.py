from django.shortcuts import render


def faraid_page(request):
    """Public, SEO-indexable calculator page."""
    return render(request, "xpert_legacy/faraid.html")


def documents_page(request):
    """Public, SEO-indexable legal document generator page."""
    return render(request, "xpert_legacy/documents.html")
