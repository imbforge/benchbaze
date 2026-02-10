from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from django.contrib import admin, messages
from django.http import FileResponse, HttpResponseRedirect
from django.utils import timezone
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily, stringWidth
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

    horizontal_scales = [100, 90, 80, 70]

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
        fontName: str = "SansR"
        fontSize: int = 7
        horizontalScale: int = 100
        overflow_title: bool = False
        content: str = ""

    def find_label_breakpoint(
        label, font_name, font_size, horizontal_scale, frame_width
    ):
        """Find the string index at which a string becomes smaller than the
        frame in which it is placed"""

        is_bigger = True
        slice_idx = len(label)

        while is_bigger:
            slice_idx -= 1
            is_bigger = (
                stringWidth(label[:slice_idx], font_name, font_size)
                * horizontal_scale
                / 100
            ) > frame_width

        return slice_idx + 1

    def find_horizontal_scale(label_width, frame_width):
        for horizontal_scale in horizontal_scales:
            label_width_scaled = label_width * horizontal_scale / 100
            if label_width_scaled < frame_width:
                return horizontal_scale

        return None

    def find_horizontal_scale_label_breakpoint(
        frame_width, label, font_name, font_size
    ):
        for horizontal_scale in horizontal_scales:
            break_index_first = find_label_breakpoint(
                label,
                font_name,
                font_size,
                horizontal_scale,
                frame_width,
            )
            second_line = label[break_index_first:].strip()

            break_index_second = find_label_breakpoint(
                second_line,
                font_name,
                font_size,
                horizontal_scale,
                frame_width,
            )

            if break_index_second < len(second_line):
                continue

        return horizontal_scale, break_index_first, break_index_second

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
                    leftPadding=0.75 * mm,
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
                        f"{queryset.model._model_abbreviation}{LAB_ABBREVIATION}",
                        f"{obj.id}",
                    ],
                )
            ]

            all_labels = main_labels + cap_labels

            # Make labels 0, 5, 6 bold
            [setattr(all_labels[i], "fontName", "SansB") for i in [0, 5, 6]]

            # Adjust style for label 3
            label_1 = all_labels[1]
            label_1.overflow_title = True

            # Adjust style for label 3
            label_3 = all_labels[3]
            label_3.rightPadding = 0

            # Adjust style for label 4
            label_4 = all_labels[4]
            label_4.leftPadding = 0
            label_4.alignment = 2
            label_4.fontSize = 6
            label_4.onOverflow = "shrink"

            # Add labels to the canvas
            for label in all_labels:
                default_style.alignment = label.alignment
                default_style.fontName = label.fontName
                default_style.fontSize = label.fontSize
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

                # When using drawText the style has to be set,
                # because it applies to Paragraph as well (?)
                label_content = str(label.content)
                text_box = canv.beginText()
                text_box.setFont(label.fontName, label.fontSize)
                text_box.setHorizScale(label.horizontalScale)
                text_box.setTextOrigin(label.x + label.leftPadding, label.y + 0.75 * mm)
                label_width = stringWidth(label_content, label.fontName, label.fontSize)
                frame_width = label.width - (label.leftPadding + label.rightPadding)

                # If label longer than frame width
                if label.overflow_title and label_width > frame_width:
                    # One line

                    ## Resize label first by squeezing it horizontally
                    if horizontal_scale := find_horizontal_scale(
                        label_width, frame_width
                    ):
                        text_box.setHorizScale(horizontal_scale)

                    ## Try reducing font size
                    elif (
                        (label_width_reduced := stringWidth(
                            label_content,
                            label.fontName,
                            reduced_font_size := label.fontSize - 1,
                        ))
                    ) < frame_width:
                        text_box.setFont(label.fontName, reduced_font_size)

                    ## Reduce size and squeeze
                    elif horizontal_scale := find_horizontal_scale(
                        label_width_reduced, frame_width
                    ):
                        text_box.setFont(label.fontName, reduced_font_size)
                        text_box.setHorizScale(horizontal_scale)

                    # Two lines
                    else:
                        text_box.setTextOrigin(
                            label.x + label.leftPadding, label.y + 1.75 * mm
                        )

                        horizontal_scale, breakpoint_first, breakpoint_second = (
                            find_horizontal_scale_label_breakpoint(
                                frame_width,
                                label_content,
                                label.fontName,
                                reduced_font_size,
                            )
                        )

                        # Continue label on next line
                        label_content_second = label_content[breakpoint_first:].strip()

                        if label_content_second:
                            # Set style of first line
                            text_box.setFont(label.fontName, reduced_font_size)
                            text_box.setHorizScale(horizontal_scale)

                            # Set second line
                            text_box_second = canv.beginText(
                                label.x + label.leftPadding,
                                label.y - 1 / 8 * inch + 2.75 * mm,
                            )
                            text_box_second.setHorizScale(horizontal_scale)
                            text_box_second.setFont(label.fontName, reduced_font_size)

                            if breakpoint_second < len(label_content_second):
                                label_content_second = label_content_second[
                                    :breakpoint_second
                                ]
                            text_box_second.textLine(text=label_content_second)
                            canv.drawText(text_box_second)

                            # Shift label 2 a little down
                            label_2 = all_labels[2]
                            label_2.y = label_2.y - 0.5 * mm

                            # Update label_content
                            label_content = label_content[:breakpoint_first]

                    text_box.textLine(text=label_content)
                    label_content = ""
                canv.drawText(text_box)
                frame.addFromList(
                    [
                        KeepInFrame(
                            0,
                            0,
                            [Paragraph(label_content, default_style)],
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
