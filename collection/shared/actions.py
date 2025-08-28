from dataclasses import dataclass

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, KeepInFrame, Paragraph

LAB_ABBREVIATION = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "XX")
BASE_DIR = getattr(settings, "BASE_DIR")

base_font_path = BASE_DIR / "static" / "fonts"
pdfmetrics.registerFont(
    TTFont("SansR", base_font_path / "LiberationSansNarrow-Regular.ttf")
)
pdfmetrics.registerFont(
    TTFont("SansB", base_font_path / "LiberationSansNarrow-Bold.ttf")
)
pdfmetrics.registerFont(
    TTFont("SansI", base_font_path / "LiberationSansNarrow-Italic.ttf")
)
pdfmetrics.registerFont(
    TTFont("SansBI", base_font_path / "LiberationSansNarrow-BoldItalic.ttf")
)
registerFontFamily(
    "Sans", normal="SansR", bold="SansB", italic="SansI", boldItalic="SansBI"
)


@admin.action(description="Create Zebra labels")
def create_zebra_label(modeladmin, request, queryset):
    """Admin action to create N0JTT-183C1-2WH labels as PDF for the Zebra
    printer
    """

    @dataclass
    class LabelFrame:
        x: float = 0
        y: float = 0
        width: float = 0
        height: float = 0
        leftPadding: float = 0
        bottomPadding: float = 0
        rightPadding: float = 0
        topPadding: float = 0
        onOverflow: str = "truncate"
        alignment: int = 0
        content: str = ""

    now = timezone.localtime(timezone.now())
    today = now.strftime("%d.%m.%y")
    model_abbreviation = queryset.model._model_abbreviation

    file_name = f"{queryset.model.__name__}_labels_{now.strftime('%Y%m%d_%H%M%S')}"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment;filename="{file_name}.pdf"'

    canv = canvas.Canvas(
        response,
        pagesize=(1.625 * inch, 0.625 * inch),
    )

    styles = getSampleStyleSheet()
    default_style = ParagraphStyle(
        "small", parent=styles["BodyText"], fontSize=7, fontName="SansR", leading=8
    )

    for obj in queryset:
        # Main label texts
        main_labels = [
            LabelFrame(
                x=1 / 16 * inch,
                y=y / 32 * inch,
                width=inch,
                height=1 / 8 * inch,
                leftPadding=1 * mm,
                rightPadding=0.5 * mm,
                content=l,
            )
            for y, l in zip(
                [15, 11, 7, 3],
                [
                    f"<b>{model_abbreviation}{LAB_ABBREVIATION}{obj.id}</b>",
                    obj.name,
                    "",
                    f"{today}\t{obj.created_by}",
                ],
            )
        ]

        # Cap label texts
        cap_labels = [
            LabelFrame(
                x=1.1875 * inch,
                y=y / 32 * inch,
                width=0.375 * inch,
                height=1 / 8 * inch,
                alignment=1,
                onOverflow="shrink",
                content=l,
            )
            for y, l in zip(
                [11, 7],
                [
                    f"<b>{model_abbreviation}{LAB_ABBREVIATION}</b>",
                    f"<b>{obj.id}</b>",
                ],
            )
        ]

        # Add the labels to the canvas
        for label in main_labels + cap_labels:
            default_style.alignment = label.alignment
            frame = Frame(
                label.x,
                label.y,
                label.width,
                label.height,
                leftPadding=label.leftPadding,
                bottomPadding=label.bottomPadding,
                rightPadding=label.rightPadding,
                topPadding=label.topPadding,
                showBoundary=0,
            )
            frame.addFromList(
                [
                    KeepInFrame(
                        0,
                        0,
                        [Paragraph(str(label.content), default_style)],
                        mode=label.onOverflow,
                    ),
                ],
                canv,
            )

        canv.showPage()

    canv.save()

    return response
