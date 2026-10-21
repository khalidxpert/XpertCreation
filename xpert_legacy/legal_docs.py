"""
xpert_legacy/legal_docs.py
Legal document generator for Pakistani use (housing society / property / court).

Design
------
Documents are plain-text templates with {{placeholders}}. `render()` validates
that every required field is present, substitutes the values, and returns clean
text. `to_html()` converts it for PDF printing (WeasyPrint, wkhtmltopdf, or the
browser's Ctrl+P).

Why templates and not free text: a wrong clause can cost someone their money.
Every document below follows the wording commonly accepted by Pakistani courts
and societies, so users fill blanks instead of writing legal language.

Run the self-test:  python3 legal_docs.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


# --------------------------------------------------------------------------- #
# Field + document models
# --------------------------------------------------------------------------- #
@dataclass
class DocField:
    name: str
    label: str
    required: bool = True
    kind: str = "text"          # text | number | date | multiline
    hint: str = ""


@dataclass
class Document:
    slug: str
    title: str
    description: str
    language: str
    fields: List[DocField]
    template: str

    @property
    def required_fields(self) -> List[str]:
        return [f.name for f in self.fields if f.required]


class MissingFields(Exception):
    def __init__(self, missing: List[str]):
        self.missing = missing
        super().__init__(f"Missing required fields: {', '.join(missing)}")


# --------------------------------------------------------------------------- #
# 1. Rent Agreement
# --------------------------------------------------------------------------- #
RENT_AGREEMENT = Document(
    slug="rent-agreement",
    title="Rent Agreement (Kiraya Nama)",
    description="Residential rent agreement between landlord and tenant.",
    language="en",
    fields=[
        DocField("landlord_name", "Landlord full name"),
        DocField("landlord_cnic", "Landlord CNIC"),
        DocField("landlord_address", "Landlord address", kind="multiline"),
        DocField("tenant_name", "Tenant full name"),
        DocField("tenant_cnic", "Tenant CNIC"),
        DocField("tenant_address", "Tenant permanent address", kind="multiline"),
        DocField("property_address", "Rented property address", kind="multiline"),
        DocField("property_type", "Property type", hint="House / Portion / Flat / Shop"),
        DocField("rent_amount", "Monthly rent (PKR)", kind="number"),
        DocField("security_deposit", "Security deposit (PKR)", kind="number"),
        DocField("rent_due_day", "Rent due day of month", kind="number", hint="e.g. 5"),
        DocField("duration_months", "Duration (months)", kind="number"),
        DocField("start_date", "Start date", kind="date"),
        DocField("notice_days", "Notice period (days)", kind="number", required=False),
        DocField("utilities", "Utilities responsibility", required=False,
                 hint="e.g. Electricity and gas paid by tenant"),
        DocField("city", "City"),
    ],
    template="""RENT AGREEMENT

This Rent Agreement is made on {{start_date}} at {{city}} between:

LANDLORD:  {{landlord_name}}, CNIC {{landlord_cnic}}, resident of
           {{landlord_address}} (hereinafter "the Landlord")

AND

TENANT:    {{tenant_name}}, CNIC {{tenant_cnic}}, resident of
           {{tenant_address}} (hereinafter "the Tenant")

WHEREAS the Landlord is the lawful owner of the premises described below and
has agreed to let them to the Tenant on the following terms.

1. PREMISES
   The Tenant shall occupy the {{property_type}} situated at:
   {{property_address}} (the "Premises").

2. TERM
   This agreement is valid for {{duration_months}} months commencing on
   {{start_date}}, and may be renewed by mutual written consent.

3. RENT
   The Tenant shall pay rent of PKR {{rent_amount}} per month, due on or
   before the {{rent_due_day}} day of each month.

4. SECURITY DEPOSIT
   The Tenant has paid PKR {{security_deposit}} as an interest-free refundable
   security deposit, to be returned at the time of vacating the Premises after
   deduction of any unpaid dues or damage beyond normal wear and tear.

5. UTILITIES
   {{utilities}}

6. OBLIGATIONS OF THE TENANT
   The Tenant shall:
   (a) use the Premises for residential purposes only;
   (b) keep the Premises in good condition and not sublet without written consent;
   (c) pay all utility bills as they fall due;
   (d) allow the Landlord reasonable access for inspection and repairs.

7. OBLIGATIONS OF THE LANDLORD
   The Landlord shall pay all applicable property taxes and shall carry out
   structural repairs not caused by the Tenant's negligence.

8. TERMINATION
   Either party may terminate this agreement by giving {{notice_days}} days
   written notice. On termination the Tenant shall hand over vacant possession.

9. DISPUTES
   Any dispute shall first be resolved amicably; failing which the competent
   courts at {{city}} shall have exclusive jurisdiction.

IN WITNESS WHEREOF the parties have signed this agreement on the date first
written above.

______________________            ______________________
LANDLORD                          TENANT
{{landlord_name}}                 {{tenant_name}}

WITNESS 1: ______________________   CNIC: ______________________
WITNESS 2: ______________________   CNIC: ______________________
""",
)


# --------------------------------------------------------------------------- #
# 2. General Affidavit
# --------------------------------------------------------------------------- #
AFFIDAVIT = Document(
    slug="affidavit",
    title="General Affidavit (Halaf Nama)",
    description="Sworn statement for name, address, income or general declarations.",
    language="en",
    fields=[
        DocField("deponent_name", "Deponent full name"),
        DocField("deponent_cnic", "Deponent CNIC"),
        DocField("deponent_address", "Deponent address", kind="multiline"),
        DocField("deponent_father", "Father's name"),
        DocField("statement", "Statement of facts", kind="multiline",
                 hint="Write the facts you are swearing to, one per line."),
        DocField("city", "City"),
        DocField("affidavit_date", "Date", kind="date"),
    ],
    template="""AFFIDAVIT

I, {{deponent_name}}, son/daughter of {{deponent_father}}, holder of CNIC
{{deponent_cnic}}, resident of {{deponent_address}}, do hereby solemnly affirm
and declare on oath as follows:

{{statement}}

I further declare that the above statement is true and correct to the best of
my knowledge, information and belief, and that nothing material has been
concealed therefrom.

DEPONENT

______________________
{{deponent_name}}
CNIC: {{deponent_cnic}}

Verified at {{city}} on this {{affidavit_date}} that the contents of the above
affidavit are true and correct.

______________________
OATH COMMISSIONER / NOTARY PUBLIC
""",
)


# --------------------------------------------------------------------------- #
# 3. Property Sale Agreement
# --------------------------------------------------------------------------- #
SALE_AGREEMENT = Document(
    slug="sale-agreement",
    title="Property Sale Agreement (Bainama)",
    description="Agreement to sell immovable property with advance payment terms.",
    language="en",
    fields=[
        DocField("seller_name", "Seller full name"),
        DocField("seller_cnic", "Seller CNIC"),
        DocField("buyer_name", "Buyer full name"),
        DocField("buyer_cnic", "Buyer CNIC"),
        DocField("property_address", "Property address", kind="multiline"),
        DocField("property_area", "Area / dimensions", hint="e.g. 5 Marla"),
        DocField("sale_price", "Total sale price (PKR)", kind="number"),
        DocField("advance_amount", "Advance paid (PKR)", kind="number"),
        DocField("balance_amount", "Balance payable (PKR)", kind="number"),
        DocField("transfer_deadline", "Deadline to complete transfer", kind="date"),
        DocField("city", "City"),
        DocField("agreement_date", "Agreement date", kind="date"),
    ],
    template="""AGREEMENT TO SELL

This Agreement to Sell is made on {{agreement_date}} at {{city}} between:

SELLER:  {{seller_name}}, CNIC {{seller_cnic}}          ("the Seller")

AND

BUYER:   {{buyer_name}}, CNIC {{buyer_cnic}}            ("the Buyer")

1. PROPERTY
   The Seller agrees to sell and the Buyer agrees to purchase the property
   measuring {{property_area}}, situated at:
   {{property_address}} (the "Property"), free from all encumbrances,
   claims, liens and litigation.

2. SALE PRICE
   The total agreed sale price of the Property is PKR {{sale_price}}.

3. PAYMENT TERMS
   (a) The Buyer has paid PKR {{advance_amount}} as advance/earnest money,
       the receipt whereof the Seller hereby acknowledges.
   (b) The balance of PKR {{balance_amount}} shall be paid at the time of
       execution of the sale deed or by {{transfer_deadline}}, whichever is
       earlier.

4. TRANSFER
   The Seller shall execute the sale deed, produce all original title
   documents, obtain the NDC from the society and appear before the concerned
   authority for transfer of the Property on or before {{transfer_deadline}}.
   All transfer charges, stamp duty and registration fee shall be borne as
   agreed between the parties at the time of transfer.

5. DEFAULT
   If the Seller fails to transfer the Property within the agreed period, the
   Buyer may claim specific performance or refund of the advance amount. If the
   Buyer fails to pay the balance, the advance shall stand forfeited.

6. POSSESSION
   Vacant and peaceful possession shall be delivered to the Buyer on receipt of
   the full sale price.

7. DISPUTES
   Disputes shall be referred to arbitration or the competent courts at
   {{city}}.

IN WITNESS WHEREOF the parties have signed this agreement.

______________________            ______________________
SELLER                            BUYER
{{seller_name}}                   {{buyer_name}}

WITNESS 1: ______________________   CNIC: ______________________
WITNESS 2: ______________________   CNIC: ______________________
""",
)


# --------------------------------------------------------------------------- #
# 4. Power of Attorney
# --------------------------------------------------------------------------- #
POWER_OF_ATTORNEY = Document(
    slug="power-of-attorney",
    title="Special Power of Attorney (Mukhtar Nama)",
    description="Authorise someone to act on your behalf for a specific matter.",
    language="en",
    fields=[
        DocField("principal_name", "Principal full name"),
        DocField("principal_cnic", "Principal CNIC"),
        DocField("principal_address", "Principal address", kind="multiline"),
        DocField("attorney_name", "Attorney (representative) full name"),
        DocField("attorney_cnic", "Attorney CNIC"),
        DocField("attorney_address", "Attorney address", kind="multiline"),
        DocField("purpose", "Purpose / powers granted", kind="multiline"),
        DocField("property_address", "Property or matter details", kind="multiline"),
        DocField("expiry", "Valid until", kind="date", required=False),
        DocField("city", "City"),
        DocField("poa_date", "Date", kind="date"),
    ],
    template="""SPECIAL POWER OF ATTORNEY

I, {{principal_name}}, CNIC {{principal_cnic}}, resident of
{{principal_address}} (the "Principal"), do hereby nominate, constitute and
appoint:

{{attorney_name}}, CNIC {{attorney_cnic}}, resident of {{attorney_address}}

as my lawful Attorney for the following specific purpose and no other:

{{purpose}}

In respect of: {{property_address}}

The Attorney is authorised to do all acts, deeds and things necessary for the
aforesaid purpose, including signing documents, appearing before the concerned
authorities and receiving or submitting papers, and to do everything lawful
that I could do myself for this purpose.

This Power of Attorney is special and limited to the purpose stated above. It
shall stand automatically revoked on completion of the purpose{{expiry_clause}}.

I hereby ratify all lawful acts done by the Attorney under this authority.

______________________
{{principal_name}}
CNIC: {{principal_cnic}}

Executed at {{city}} on {{poa_date}}.

WITNESS 1: ______________________   CNIC: ______________________
WITNESS 2: ______________________   CNIC: ______________________
""",
)


# --------------------------------------------------------------------------- #
# 5. Society No Demand Certificate
# --------------------------------------------------------------------------- #
NDC = Document(
    slug="society-ndc",
    title="No Demand Certificate (NDC)",
    description="Society-issued clearance for property transfer or utilities.",
    language="en",
    fields=[
        DocField("society_name", "Society name"),
        DocField("member_name", "Member / owner name"),
        DocField("house_no", "House / plot number"),
        DocField("block", "Block / street", required=False),
        DocField("area", "Area (e.g. 5 Marla)", required=False),
        DocField("dues_cleared_upto", "Dues cleared up to (month/year)"),
        DocField("purpose", "Purpose of certificate"),
        DocField("issue_date", "Issue date", kind="date"),
        DocField("secretary_name", "Secretary name"),
    ],
    template="""{{society_name}}

NO DEMAND CERTIFICATE

Date: {{issue_date}}

This is to certify that Mr./Mrs. {{member_name}}, holder of House/Plot No.
{{house_no}}{{block_clause}}{{area_clause}}, is a member of this Society and
that all dues payable to the Society, including maintenance charges, development
charges and utility charges, have been cleared up to {{dues_cleared_upto}}.

As of the date of this certificate there are NO outstanding dues or demands
against the above-mentioned property or its owner.

This certificate is issued on the request of the member for the purpose of:
{{purpose}}

This certificate is valid for a period of thirty (30) days from the date of
issue and is subject to verification of records.

______________________
{{secretary_name}}
Secretary, {{society_name}}
""",
)


DOCUMENTS: Dict[str, Document] = {
    d.slug: d
    for d in (RENT_AGREEMENT, AFFIDAVIT, SALE_AGREEMENT, POWER_OF_ATTORNEY, NDC)
}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def list_documents() -> List[Dict]:
    """Metadata for the UI — no template bodies."""
    return [
        {
            "slug": d.slug,
            "title": d.title,
            "description": d.description,
            "language": d.language,
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "required": f.required,
                    "kind": f.kind,
                    "hint": f.hint,
                }
                for f in d.fields
            ],
        }
        for d in DOCUMENTS.values()
    ]


def _conditional_clauses(data: Dict[str, str]) -> Dict[str, str]:
    """Build the small optional fragments the templates expect."""
    out = dict(data)

    out["block_clause"] = f", Block {data['block']}" if data.get("block") else ""
    out["area_clause"] = f", Area: {data['area']}" if data.get("area") else ""
    out["expiry_clause"] = (
        f" or on {data['expiry']}, whichever is earlier" if data.get("expiry") else ""
    )

    # Multiline values -> indented paragraphs
    if data.get("statement"):
        lines = [ln.strip() for ln in data["statement"].splitlines() if ln.strip()]
        out["statement"] = "\n".join(
            f"{i}. {ln}" for i, ln in enumerate(lines, start=1)
        )
    return out


def render(slug: str, data: Dict[str, str]) -> str:
    """
    Fill `slug`'s template with `data`.

    Raises KeyError for an unknown slug and MissingFields when a required
    field is empty.
    """
    doc = DOCUMENTS.get(slug)
    if doc is None:
        raise KeyError(f"Unknown document: {slug}")

    missing = [
        f.label
        for f in doc.fields
        if f.required and not str(data.get(f.name, "")).strip()
    ]
    if missing:
        raise MissingFields(missing)

    values = _conditional_clauses(
        {k: ("" if v is None else str(v).strip()) for k, v in data.items()}
    )

    # Any required-but-optional placeholder not supplied becomes empty
    for f in doc.fields:
        values.setdefault(f.name, "")

    def substitute(match: "re.Match[str]") -> str:
        key = match.group(1)
        return values.get(key, "")

    text = PLACEHOLDER.sub(substitute, doc.template)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def to_html(text: str, title: str = "Legal Document") -> str:
    """Minimal, print-ready HTML (feed to WeasyPrint or the browser print dialog)."""
    body = "\n".join(
        f"<p>{line}</p>" if line.strip() else "<p>&nbsp;</p>"
        for line in text.splitlines()
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  @page {{ size: A4; margin: 22mm 18mm; }}
  body {{ font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.55;
         color: #111; }}
  p {{ margin: 0; white-space: pre-wrap; }}
</style></head><body>{body}</body></html>"""


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    sample = {
        "rent-agreement": {
            "landlord_name": "Muhammad Aslam",
            "landlord_cnic": "35202-1234567-1",
            "landlord_address": "House 12, Gulberg III, Lahore",
            "tenant_name": "Bilal Ahmed",
            "tenant_cnic": "35201-7654321-9",
            "tenant_address": "Flat 4, Model Town, Lahore",
            "property_address": "House 45, Block B, Johar Town, Lahore",
            "property_type": "House",
            "rent_amount": "45000",
            "security_deposit": "90000",
            "rent_due_day": "5",
            "duration_months": "12",
            "start_date": "01-11-2026",
            "notice_days": "30",
            "utilities": "Electricity and gas bills shall be paid by the Tenant.",
            "city": "Lahore",
        },
        "affidavit": {
            "deponent_name": "Syed Khalid Hussain Shah",
            "deponent_cnic": "35202-1111111-1",
            "deponent_address": "1-S-3B/2, Ghazali Park, Wahdat Colony, Lahore",
            "deponent_father": "Syed Hussain Shah",
            "statement": "That I am a resident of Lahore.\nThat my name is correctly spelled as above.",
            "city": "Lahore",
            "affidavit_date": "20-10-2026",
        },
        "sale-agreement": {
            "seller_name": "Ayesha Khan",
            "seller_cnic": "35202-2222222-2",
            "buyer_name": "Usman Tariq",
            "buyer_cnic": "35202-3333333-3",
            "property_address": "Plot 88, Sector C, Bahria Town, Lahore",
            "property_area": "10 Marla",
            "sale_price": "18500000",
            "advance_amount": "2000000",
            "balance_amount": "16500000",
            "transfer_deadline": "31-12-2026",
            "city": "Lahore",
            "agreement_date": "20-10-2026",
        },
        "power-of-attorney": {
            "principal_name": "Fatima Bibi",
            "principal_cnic": "35202-4444444-4",
            "principal_address": "House 9, Shadman, Lahore",
            "attorney_name": "Ali Raza",
            "attorney_cnic": "35202-5555555-5",
            "attorney_address": "House 21, Iqbal Town, Lahore",
            "purpose": "To appear before LDA and complete the transfer of the property.",
            "property_address": "Plot 14, Block D, Johar Town, Lahore",
            "expiry": "31-12-2026",
            "city": "Lahore",
            "poa_date": "20-10-2026",
        },
        "society-ndc": {
            "society_name": "Ghazali Park Housing Society",
            "member_name": "Muhammad Yousaf",
            "house_no": "112-B",
            "block": "C",
            "area": "5 Marla",
            "dues_cleared_upto": "October 2026",
            "purpose": "Transfer of property to a buyer.",
            "issue_date": "20-10-2026",
            "secretary_name": "Syed Khalid Hussain Shah",
        },
    }

    ok = True
    for slug, payload in sample.items():
        try:
            out = render(slug, payload)
        except MissingFields as exc:
            ok = False
            print(f"FAIL {slug}: {exc}")
            continue
        leftover = PLACEHOLDER.findall(out)
        status = "PASS" if not leftover else f"FAIL leftover={leftover}"
        if leftover:
            ok = False
        print(f"{status}  {slug:20s} {len(out.splitlines()):3d} lines")
        print("-" * 70)
        print("\n".join(out.splitlines()[:6]))
        print("...\n")

    try:
        render("affidavit", {"deponent_name": "X"})
        print("FAIL validation did not trigger")
        ok = False
    except MissingFields as exc:
        print(f"PASS validation correctly rejected: {len(exc.missing)} missing fields")

    print("\nALL PASSED" if ok else "\nSOME FAILED")
