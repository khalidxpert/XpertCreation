import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .faraid import Heirs, calculate
from .legal_docs import MissingFields, list_documents, render, to_html
from .models import LegalDocumentRequest

HEIR_TYPES = {
    "husband": bool,
    "father": bool,
    "mother": bool,
    "paternal_grandfather": bool,
    "paternal_grandmother": bool,
    "maternal_grandmother": bool,
    "wives": int,
    "sons": int,
    "daughters": int,
    "grandsons": int,
    "granddaughters": int,
    "full_brothers": int,
    "full_sisters": int,
    "paternal_brothers": int,
    "paternal_sisters": int,
    "maternal_siblings": int,
    "full_nephews": int,
}

MAX_COUNT = 20


def _body(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _clean_heirs(raw):
    """Whitelist keys and coerce types — never trust the client."""
    clean = {}
    for key, typ in HEIR_TYPES.items():
        value = raw.get(key, False if typ is bool else 0)
        if typ is bool:
            clean[key] = bool(value)
        else:
            try:
                n = int(value)
            except (TypeError, ValueError):
                n = 0
            clean[key] = max(0, min(n, MAX_COUNT))
    return clean


@csrf_exempt
@require_POST
def faraid_api(request):
    """
    POST /api/faraid/
    {"estate": 5000000, "wives": 1, "sons": 2, "daughters": 1,
     "mother": true, "father": true}
    """
    try:
        payload = _body(request)
    except ValueError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    estate = payload.get("estate")
    if estate in (None, ""):
        return JsonResponse({"error": "estate is required."}, status=400)

    try:
        estate = float(estate)
    except (TypeError, ValueError):
        return JsonResponse({"error": "estate must be a number."}, status=400)

    if estate <= 0:
        return JsonResponse({"error": "estate must be greater than zero."}, status=400)

    try:
        result = calculate(estate, Heirs(**_clean_heirs(payload)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    result["disclaimer"] = (
        "This is a calculation aid only. Confirm the distribution with a "
        "qualified scholar before transferring any property."
    )
    result["wasiyyah_hint"] = (
        "Wasiyyah (a will) is limited to one-third of the estate before "
        "distribution. Debts are paid first."
    )
    return JsonResponse(result)


@require_GET
def documents_api(request):
    """GET /api/legal/documents/ — field metadata for the picker screen."""
    return JsonResponse({"documents": list_documents()})


@csrf_exempt
@require_POST
def render_document_api(request):
    """
    POST /api/legal/render/
    {"slug": "rent-agreement", "data": {...}}
    """
    try:
        payload = _body(request)
    except ValueError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    slug = payload.get("slug", "")
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return JsonResponse({"error": "data must be an object."}, status=400)

    try:
        text = render(slug, data)
    except KeyError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except MissingFields as exc:
        return JsonResponse(
            {"error": "Missing required fields.", "missing": exc.missing},
            status=422,
        )

    record = LegalDocumentRequest.objects.create(
        user=request.user if request.user.is_authenticated else None,
        doc_type=slug,
        # CNIC never leaves the server-side payload
        payload={k: v for k, v in data.items() if "cnic" not in k.lower()},
    )

    return JsonResponse(
        {
            "text": text,
            "reference_no": record.reference_no,
            "download_url": f"/api/legal/pdf/{record.reference_no}/",
        }
    )


@require_GET
def document_pdf(request, reference_no: str):
    """
    GET /api/legal/pdf/<ref>/ — printable HTML (Ctrl+P -> PDF).

    For a real PDF stream, install WeasyPrint and swap the last two lines:
        from weasyprint import HTML
        return HttpResponse(HTML(string=html).write_pdf(),
                            content_type="application/pdf")
    """
    record = LegalDocumentRequest.objects.filter(reference_no=reference_no).first()
    if record is None:
        return JsonResponse({"error": "Not found."}, status=404)

    text = render(record.doc_type, record.payload)
    html = to_html(text, title=record.get_doc_type_display())
    return HttpResponse(html, content_type="text/html; charset=utf-8")
