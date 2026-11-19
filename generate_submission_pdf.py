import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

pdf_path = "Swiggy_Growth_ResolveAI_Submission.pdf"
doc = SimpleDocTemplate(
    pdf_path,
    pagesize=letter,
    rightMargin=54,
    leftMargin=54,
    topMargin=54,
    bottomMargin=54
)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=22,
    leading=26,
    textColor=colors.HexColor('#FC8019'),
    spaceAfter=4
)

subtitle_style = ParagraphStyle(
    'DocSubtitle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=14,
    textColor=colors.HexColor('#282C3F'),
    spaceAfter=14
)

section_heading = ParagraphStyle(
    'SectionHeading',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=15,
    textColor=colors.HexColor('#FC8019'),
    spaceBefore=8,
    spaceAfter=3
)

body_style = ParagraphStyle(
    'BodyTextCustom',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.HexColor('#3D4152'),
    spaceAfter=8
)

link_style = ParagraphStyle(
    'LinkStyle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=10.5,
    leading=15,
    textColor=colors.HexColor('#FC8019'),
    spaceAfter=4
)

meta_style = ParagraphStyle(
    'MetaText',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=8.5,
    leading=11,
    textColor=colors.HexColor('#686B78')
)

story = []

# Header
story.append(Paragraph("Swiggy Growth Submission: ResolveAI", title_style))
story.append(Paragraph("Proactive Order Intelligence & Autonomous Issue Recovery Platform", subtitle_style))
story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#FC8019'), spaceAfter=14))

# Section 1: Who It's For
story.append(Paragraph("1. WHO IT'S FOR", section_heading))
story.append(Paragraph("Swiggy Delivery Operations Managers, Restaurant Partners, and Hungry Customers across high-density delivery clusters.", body_style))

# Section 2: The Problem
story.append(Paragraph("2. THE PROBLEM", section_heading))
story.append(Paragraph("Food delivery delays are handled reactively. When kitchen congestion, weather, or rider shortages stall an order, customers only find out when their meal is already late. This fuels repetitive <i>'Where is my order?'</i> support tickets, damages restaurant partner ratings, and causes customer churn before anyone can intervene.", body_style))

# Section 3: The Solution
story.append(Paragraph("3. OUR SOLUTION (SWIGGY RESOLVEAI)", section_heading))
story.append(Paragraph("ResolveAI is an autonomous order intelligence and early recovery engine. Instead of waiting for complaints, ResolveAI analyzes kitchen prep times, rider transit telemetry, and historical order data to forecast delivery risks 15–20 minutes in advance. When high delay risk is detected, multi-agent AI coordinates an immediate, automated resolution: alerting restaurant staff, dispatching backup delivery partners, and sending proactive customer updates with goodwill vouchers—governed by operational approval safety rules.", body_style))

# Section 4: Why It Matters
story.append(Paragraph("4. WHY IT MATTERS", section_heading))
story.append(Paragraph("Proactivity transforms potential cancellations into brand-loyalty moments. By resolving operational bottlenecks before the customer complains, ResolveAI slashes support escalations, protects restaurant reputations, and preserves customer trust when unexpected delays occur.", body_style))

# Section 5: Prototype & Code Links Box
story.append(Spacer(1, 10))
proto_data = [
    [
        Paragraph("<b>WORKING PROTOTYPE & REPOSITORY:</b><br/>"
                  "&bull; <b>Live Application:</b> <font color='#FC8019'><u>https://swiggy-resolve-ai.vercel.app</u></font><br/>"
                  "&bull; <b>GitHub Repository:</b> <font color='#FC8019'><u>https://github.com/Gnanendhra28/Swiggy-ResolveAI</u></font><br/>"
                  "<font size=8.5 color='#686B78'>Full-stack autonomous system built with GenAI agents, Next.js 16, FastAPI, LightGBM, and Neon PostgreSQL.</font>", 
                  link_style)
    ]
]
proto_table = Table(proto_data, colWidths=[7.0*inch])
proto_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF5ED')),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FED7AA')),
    ('PADDING', (0,0), (-1,-1), 10),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
story.append(proto_table)

doc.build(story)
print(f"PDF generated successfully at {pdf_path}, size: {os.path.getsize(pdf_path)} bytes")
