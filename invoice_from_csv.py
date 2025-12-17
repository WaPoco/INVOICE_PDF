import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

def money(d: Decimal) -> str:
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{d:.2f}".replace(".", ",")
    return f"{s} €"

def get_current_date_str():
    return datetime.now().strftime("%d.%m.%Y")

def parse_decimal(s: str) -> Decimal:
    # "45 min" -> Decimal("45")
    numb = s.strip().replace(" min", "")
    return Decimal(numb or "0")

def read_items(csv_path: Path):
    items = []
    text = Path(csv_path).read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    records = []
    for i in range(0, len(lines), 2):
        line1 = lines[i].split(";")
        line2 = lines[i+1].split(";")

        record = {
            "Datum": line1[0],
            "Begin": line1[1],
            "Dauer": line2[0],
            "Ort": line2[1],
        }
        records.append(record)
    return records

def make_invoice_pdf(csv_path: str, out_pdf: str):
    # ===== Muster / Stammdaten anpassen =====
    seller = {
        "name": "Vasile Pogorelov",
        "addr": "Lietzenburger Str. 7\n10789 Berlin",
        "email": "vasili-pogorelov@web.de",
        "iban": "DE00 0000 0000 0000 0000 00",
        "bic": "XXXXXXXXXXX",
        "tax_id": "USt-IdNr. / Steuernr.",
    }
    buyer = {
        "name": "Intellego GmbH",
        "addr": "Bornitzstraße 73-75\n10365 Berlin",
    }
    invoice_no = "RE-2025-001"
    # i need a fucntion that genrates the current date in dd.mm.yyyy format

    invoice_date = get_current_date_str()
    service_date = "16.12.2025"
    vat_rate = Decimal("0.19")   # 0.19 / 0.07 / 0.00

    # ===== Daten einlesen =====
    items = read_items(Path(csv_path))
    if not items:
        raise SystemExit("Keine Positionen in der CSV gefunden (Header/Delimiter prüfen).")

    # ===== PDF bauen =====
    c = canvas.Canvas(out_pdf, pagesize=A4)
    w, h = A4
    total_hour = sum(parse_decimal(it["Dauer"]) for it in items)
    net = total_hour * 32 / 60
    margin = 18 * mm
    x0 = margin
    y = h - margin

    # Kopf: Absender links
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y, seller["name"])
    c.setFont("Helvetica", 10)
    y -= 5*mm
    for line in seller["addr"].split("\n"):
        c.drawString(x0, y, line); y -= 4.2*mm
    c.drawString(x0, y, seller["email"])

    # Kopf: Rechnung meta rechts
    meta_x = w - margin - 70*mm
    meta_y = h - margin
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(w - margin, meta_y, "RECHNUNG")
    c.setFont("Helvetica", 10)
    meta_y -= 8*mm
    c.drawString(meta_x, meta_y, f"Rechnungsnr.: {invoice_no}"); meta_y -= 5*mm
    c.drawString(meta_x, meta_y, f"Rechnungsdatum: {invoice_date}"); meta_y -= 5*mm
    c.drawString(meta_x, meta_y, f"Leistungsdatum: {service_date}")

    # Empfängerblock
    y = h - margin - 40*mm
    c.setFont("Helvetica", 10)
    #c.drawString(x0, y, seller["name"] + " · " + seller["addr"].replace("\n", " · "))
    y -= 8*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, buyer["name"]); y -= 5*mm
    c.setFont("Helvetica", 10)
    for line in buyer["addr"].split("\n"):
        c.drawString(x0, y, line); y -= 4.2*mm

    # Tabelle Header
    y -= 6*mm
    c.setFont("Helvetica-Bold", 10)
    c.line(x0, y, w - margin, y); y -= 6*mm
    c.drawString(x0, y, "#")
    c.drawString(x0 + 10*mm, y, "Datum")
    c.drawString(x0 + 35*mm, y, "Begin")
    c.drawString(x0 + 55*mm, y, "Ort")
    c.drawRightString(w - margin - 45*mm, y, "Dauer")
    y -= 4*mm
    c.line(x0, y, w - margin, y); y -= 7*mm
    c.setFont("Helvetica", 10)

    # Tabellenzeilen
    row_h = 7*mm
    for i, it in enumerate(items, start=1):
        # Seitenumbruch
        if y < margin + 50*mm:
            c.showPage()
            y = h - margin
            c.setFont("Helvetica", 10)

        c.drawString(x0 + 10*mm, y, it["Datum"])
        c.drawString(x0 + 35*mm, y, it["Begin"])
        c.drawString(x0 + 55*mm, y, it["Ort"])
        c.drawString(w - margin - 45*mm, y, it["Dauer"])
        y -= row_h

    # Summenblock
    y -= 4*mm
    c.line(x0, y, w - margin, y); y -= 10*mm

    sum_x_label = w - margin - 60*mm
    sum_x_value = w - margin

    c.setFont("Helvetica", 10)
    c.drawString(sum_x_label, y, "Zwischensumme (Stunden)")
    c.drawRightString(sum_x_value, y, money(total_hour / 60)); y -= 6*mm

    y -= 6*mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(sum_x_label, y, "Gesamtbetrag")
    c.drawRightString(sum_x_value, y, money(net)); y -= 12*mm

    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Hinweis: Kein Ausweis von Umsatzsteuer, da Kleinunternehmer gemäß § 19 UStG.")
    y -= 15*mm
    # Zahlung
    c.setFont("Helvetica", 10)
    c.drawString(x0, y, "Bitte überweisen Sie den Gesamtbetrag innerhalb von 14 Tagen auf:"); y -= 6*mm
    c.drawString(x0, y, f"IBAN: {seller['iban']}   BIC: {seller['bic']}"); y -= 10*mm
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, f"Steuernr./USt-IdNr.: {seller['tax_id']}")

    c.save()
    print(f"✅ PDF erstellt: {out_pdf}")

if __name__ == "__main__":
    make_invoice_pdf("daten.csv", "rechnung.pdf")

