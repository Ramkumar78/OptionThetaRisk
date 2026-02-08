import io
import logging
from typing import Dict, List, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_trade_audit_pdf(data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a PDF trade audit report based on the analysis data.
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Heading1'], alignment=1))
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'], spaceAfter=12))
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=9, leading=11))

    story = []

    # --- 1. Header ---
    title = Paragraph("Trade Audit Report", styles['CenterTitle'])
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_line = Paragraph(f"Generated on: {date_str}", styles['Normal'])

    story.append(title)
    story.append(Spacer(1, 12))
    story.append(date_line)
    story.append(Spacer(1, 24))

    # --- 2. Executive Summary ---
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))

    metrics = data.get("metrics", {})
    strat_metrics = data.get("strategy_metrics", {})
    verdict = data.get("verdict", "N/A")
    verdict_color = data.get("verdict_color", "black")

    # Metrics Table
    summary_data = [
        ["Metric", "Value"],
        ["Total PnL (Net)", f"${metrics.get('total_pnl', 0):,.2f}"],
        ["Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%"],
        ["Profit Factor", f"{strat_metrics.get('profit_factor', 'N/A')}"], # PF might not be in root, let's check
        ["Num Trades", f"{metrics.get('num_trades', 0)}"],
        ["Verdict", verdict]
    ]

    # Check if Profit Factor is available, otherwise calculate or omit
    # data['strategy_metrics'] usually has keys like 'win_rate', 'total_pnl', 'total_fees' etc.
    # calculate_csv returns 'metrics' and 'strategy_metrics'.
    # I'll rely on what's available or simple calc.
    # Profit Factor = Gross Profit / Gross Loss. Not explicitly in strategy_metrics based on read_file.
    # I can calculate it if needed, but for now let's stick to what's easily available.

    table = Table(summary_data, colWidths=[200, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Highlight Verdict Color
    if verdict_color == "red":
        v_color = colors.red
    elif verdict_color == "green":
        v_color = colors.green
    elif verdict_color == "yellow":
        v_color = colors.orange
    else:
        v_color = colors.black

    # We can't easily change just one cell color in reportlab Table data structure after init,
    # but we can add a style command.
    # Verdict is the last row, second column (1, 5)
    table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 5), (1, 5), v_color),
        ('FONTNAME', (1, 5), (1, 5), 'Helvetica-Bold'),
    ]))

    story.append(table)
    story.append(Spacer(1, 24))

    # --- 3. Behavioral Analysis ---
    story.append(Paragraph("Behavioral Analysis", styles['SectionHeader']))

    disc_score = data.get("discipline_score", 0)
    disc_details = data.get("discipline_details", [])

    score_text = f"Discipline Score: {disc_score}/100"
    score_para = Paragraph(score_text, styles['Heading3'])
    story.append(score_para)

    if disc_details:
        for detail in disc_details:
            # Color code based on +/-
            color = "green" if "+" in detail else "red"
            text = f"<font color='{color}'>• {detail}</font>"
            story.append(Paragraph(text, styles['Normal']))
    else:
        story.append(Paragraph("No significant behavioral flags detected.", styles['Normal']))

    story.append(Spacer(1, 24))

    # --- 4. Performance Charts ---
    story.append(Paragraph("Performance Charts", styles['SectionHeader']))

    portfolio_curve = data.get("portfolio_curve", [])
    if portfolio_curve:
        # Create Chart
        chart_buf = _create_pnl_chart(portfolio_curve)
        if chart_buf:
            img = Image(chart_buf, width=400, height=250)
            story.append(img)
    else:
        story.append(Paragraph("Not enough data for performance chart.", styles['Normal']))

    story.append(Spacer(1, 24))

    # --- 5. Path to Alpha (Recommendations) ---
    story.append(Paragraph("Path to Alpha", styles['SectionHeader']))

    recommendations = _generate_recommendations(data)

    if recommendations:
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", styles['Normal']))
    else:
        story.append(Paragraph("Keep up the good work! No critical improvements identified.", styles['Normal']))

    story.append(Spacer(1, 24))

    # --- 6. Detailed Metrics (Optional) ---
    story.append(Paragraph("Leakage Report", styles['SectionHeader']))
    leakage = data.get("leakage_report", {})
    fee_drag = leakage.get("fee_drag", 0)

    story.append(Paragraph(f"Fee Drag: {fee_drag}% (Target: < 10%)", styles['Normal']))

    stale = leakage.get("stale_capital", [])
    if stale:
        story.append(Paragraph(f"Stale Capital Detected: {len(stale)} positions held > 10 days with < $1/day return.", styles['Normal']))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def _create_pnl_chart(portfolio_curve: List[Dict]) -> io.BytesIO:
    """Generates a PnL chart image."""
    if not portfolio_curve:
        return None

    try:
        df = pd.DataFrame(portfolio_curve)
        df['x'] = pd.to_datetime(df['x'])
        df = df.sort_values('x')

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(df['x'], df['y'], marker='o', linestyle='-', markersize=4)
        ax.set_title("Cumulative PnL")
        ax.set_ylabel("PnL ($)")
        ax.set_xlabel("Date")
        ax.grid(True, linestyle='--', alpha=0.6)

        # Format dates
        fig.autofmt_xdate()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Failed to generate chart: {e}")
        return None

def _generate_recommendations(data: Dict) -> List[str]:
    """Generates actionable recommendations based on analysis data."""
    recs = []

    # 1. Fee Drag
    leakage = data.get("leakage_report", {})
    fee_drag = leakage.get("fee_drag", 0)
    if fee_drag > 15.0:
        recs.append("CRITICAL: Fee Drag is very high (>15%). Stop trading 1-wide spreads or low-priced options.")
    elif fee_drag > 10.0:
        recs.append("WARNING: Fee Drag is high (>10%). Consider widening spreads or reducing frequency.")

    # 2. Win Rate
    metrics = data.get("metrics", {})
    win_rate = metrics.get("win_rate", 0)
    if win_rate < 0.40:
        recs.append("Win Rate is low (<40%). Review your entry criteria and directional bias.")

    # 3. Discipline
    disc_score = data.get("discipline_score", 100)
    if disc_score < 70:
        recs.append("Behavioral Score is low. Focus on eliminating Revenge Trading and Tilt.")

    # 4. Stale Capital
    stale = leakage.get("stale_capital", [])
    if len(stale) > 2:
        recs.append(f"Capital Efficiency: You have {len(stale)} stale positions. Close them to free up buying power.")

    # 5. Risk / Drawdown
    strat_metrics = data.get("strategy_metrics", {})
    max_dd = strat_metrics.get("max_drawdown", 0)
    total_pnl = strat_metrics.get("total_pnl", 0)

    if total_pnl > 0 and max_dd > (total_pnl * 0.5):
        recs.append("High Drawdown relative to profits. Review position sizing.")

    # 6. ITM Risk
    verdict = data.get("verdict", "")
    if "Red Flag" in verdict and "ITM" in verdict:
         recs.append("IMMEDIATE ACTION: Close or Roll deep ITM short positions to avoid assignment risk.")

    if not recs:
        recs.append("Continue monitoring your detailed trade logs for minor improvements.")

    return recs
