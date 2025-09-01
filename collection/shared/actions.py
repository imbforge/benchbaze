from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from django.contrib import admin, messages
from django.http import FileResponse, HttpResponseRedirect
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


@admin.action(description="Create labels")
def create_label(modeladmin, request, queryset):
    """
    Admin action to create labels as PDF
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

    def create_n0jtt_zebra_label(queryset, now):
        """
        For N0JTT-183C1-2WH Zebra labels

        -------------
        |     0     |
        -------------   ---------
        |     1     |   |   5   |
        -------------   ---------
        |     2     |   |   6   |
        -------------   ---------
        |  3  |  4  |
        -------------

        The contents of 1, 6 and 7 are always:
        0 -> [model abbreviation][lab abbreviation][object ID], e.g. pHU1234
        5 -> [model abbreviation][lab abbreviation], e.g. pHU
        6 -> [object ID], e.g. 1234

        The other fields, 1-4 are editable
        """

        styles = getSampleStyleSheet()
        default_style = ParagraphStyle(
            "small", parent=styles["BodyText"], fontSize=7, fontName="SansR", leading=8
        )
        today = now.strftime("%d.%m.%y")
        buffer = BytesIO()
        canv = canvas.Canvas(
            buffer,
            pagesize=(
                1.625 * inch,
                0.625 * inch,
            ),
        )

        for obj in queryset:
            # Labels in rectangle, 0-4

            zebra_n0jtt_label_content = obj.zebra_n0jtt_label_content
            zebra_n0jtt_label_content[3] = today
            main_labels = [
                LabelFrame(
                    x=x * inch,
                    y=y / 32 * inch,
                    width=width,
                    height=1 / 8 * inch,
                    leftPadding=1 * mm,
                    rightPadding=0.5 * mm,
                    content=l,
                )
                for x, y, width, l in zip(
                    [1 / 16] * 4 + [1 / 16 + 0.38],
                    [15, 11, 7, 3, 3],
                    [inch] * 3 + [inch * 0.38, inch * 0.62],
                    zebra_n0jtt_label_content,
                )
            ]

            # Adjust style for label 3
            label_3 = main_labels[3]
            label_3.rightPadding = 0

            # Adjust style for label 4
            label_4 = main_labels[4]
            label_4.leftPadding = 0
            label_4.alignment = 2
            label_4.onOverflow = "shrink"

            # Labels in circle, 5-6
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
                        f"<b>{queryset.model._model_abbreviation}{LAB_ABBREVIATION}</b>",
                        f"<b>{obj.id}</b>",
                    ],
                )
            ]

            # Add labels to the canvas
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

        buffer.seek(0)
        return buffer

    label_name = request.POST.get("format", default="none")

    # Check if label format submitted with form is available
    label_formats = ("N0JTT-183C1-2WH",)
    if label_name not in label_formats:
        messages.error(
            request, "Cannot create labels. No matching label format can be found."
        )
        return HttpResponseRedirect(".")

    # Create response
    now = timezone.localtime(timezone.now())
    file_name = f"{queryset.model.__name__}_labels_{now.strftime('%Y%m%d_%H%M%S')}.pdf"

    # Create labels
    labels = None
    if label_name == "N0JTT-183C1-2WH":
        labels = create_n0jtt_zebra_label(queryset, now)

    return FileResponse(labels, as_attachment=True, filename=file_name)
