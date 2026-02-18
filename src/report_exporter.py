"""
Report Exporter
===============
Generates export-ready reports from campus scan results.
Formats: CSV (itemized interventions), JSON (full data), Text summary.

These are the deliverables an administrator can attach to a budget proposal
or present to a facilities committee on Monday morning.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_DIR

REPORTS_DIR = DATA_DIR / "reports"


class ReportExporter:
    """Exports campus scan + ROI results in multiple formats."""

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    # ── JSON export ───────────────────────────────────────────────────────────

    def export_json(self, report: Dict, filename: str = None) -> str:
        filename = filename or f"campus_report_{self._timestamp()}.json"
        path = REPORTS_DIR / filename
        with open(path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  JSON report: {path}")
        return str(path)

    # ── CSV: intervention itemization ─────────────────────────────────────────

    def export_interventions_csv(self, report: Dict,
                                  filename: str = None) -> str:
        """
        Exports a flat CSV of all interventions across all hotspots.
        Format suitable for budget proposals and spreadsheet import.
        """
        filename = filename or f"interventions_{self._timestamp()}.csv"
        path = REPORTS_DIR / filename

        rows = []
        for spot in report.get('top_hotspots', []):
            roi = spot.get('roi', {})
            for iv in roi.get('interventions', []):
                rows.append({
                    'Rank':                   spot['rank'],
                    'Location':               spot['location_name'],
                    'Risk Level':             spot['risk_level'],
                    'Risk Score':             spot['risk_score'],
                    'Incident Count':         spot['incident_count'],
                    'Dominant Crime':         spot.get('dominant_crime', 'N/A'),
                    'VIIRS Luminance':        spot.get('viirs_luminance', 'N/A'),
                    'VIIRS Label':            spot.get('viirs_label', 'N/A'),
                    'CPTED Priority':         spot['cpted_priority'],
                    'Intervention Priority':  iv['priority'],
                    'Intervention':           iv['name'],
                    'Quantity':               iv['quantity'],
                    'Location Note':          iv['location_note'],
                    'Unit Cost ($)':          iv['unit_cost'],
                    'Total Cost ($)':         iv['total_cost'],
                    'Annual Maintenance ($)': iv['annual_maintenance'],
                    'Cost Tier':              iv['cost_tier'],
                    'Reduction % Low':        iv['reduction_pct_low'],
                    'Reduction % High':       iv['reduction_pct_high'],
                    'Reduction % Median':     iv['reduction_pct_median'],
                    'Incidents Prevented/yr': iv['incidents_prevented'],
                    'Annual Savings ($)':     iv['annual_savings'],
                    'Citation Count':         iv['citation_count'],
                    'Citations':              ' | '.join(
                        f"{c['authors']} ({c['year']})"
                        for c in iv['citations']
                    ),
                })

        if not rows:
            print("  No intervention data to export")
            return ''

        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        print(f"  Interventions CSV: {path} ({len(rows)} rows)")
        return str(path)

    # ── CSV: campus risk scores ───────────────────────────────────────────────

    def export_risk_scores_csv(self, report: Dict,
                                filename: str = None) -> str:
        """Exports all location risk scores as a flat CSV."""
        filename = filename or f"risk_scores_{self._timestamp()}.csv"
        path = REPORTS_DIR / filename

        rows = []
        for loc in report.get('all_locations_scored', []):
            rows.append({
                'Location':       loc['location_name'],
                'Latitude':       loc['lat'],
                'Longitude':      loc['lon'],
                'Risk Level':     loc['risk_level'],
                'Risk Score':     loc['risk_score'],
                'Incident Count': loc['incident_count'],
            })

        if not rows:
            return ''

        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        print(f"  Risk scores CSV: {path} ({len(rows)} locations)")
        return str(path)

    # ── Text executive summary ────────────────────────────────────────────────

    def export_executive_summary(self, report: Dict,
                                  filename: str = None) -> str:
        """
        Generates a plain-text executive summary suitable for
        email attachment or conversion to PDF.
        """
        filename = filename or f"executive_summary_{self._timestamp()}.txt"
        path = REPORTS_DIR / filename

        now    = report.get('generated_date', datetime.now().strftime('%B %d, %Y'))
        summary = report.get('campus_risk_summary', {})
        gaps   = report.get('infrastructure_gaps', {})
        spots  = report.get('top_hotspots', [])

        # Total financials across all hotspots
        total_cost     = sum(s.get('roi', {}).get('financials', {}).get('total_infrastructure_cost', 0)
                            for s in spots)
        total_savings  = sum(s.get('roi', {}).get('financials', {}).get('total_annual_savings', 0)
                            for s in spots)
        total_prevented = sum(s.get('roi', {}).get('financials', {}).get('total_incidents_prevented', 0)
                              for s in spots)

        lines = [
            "=" * 70,
            "MIZZOU CAMPUS SAFETY INFRASTRUCTURE REPORT",
            "Generated by TigerTown CPTED Analysis System",
            f"Date: {now}",
            f"Scan Time: {report.get('scan_time_label', 'N/A')}",
            "=" * 70,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 70,
            f"Locations Scanned:         {report.get('locations_scanned', 0)}",
            f"High-Risk Locations:       {summary.get('high_risk_locations', 0)}",
            f"Medium-Risk Locations:     {summary.get('medium_risk_locations', 0)}",
            f"Campus Risk Index:         {summary.get('campus_risk_index', 0):.1f}/10",
            "",
            "INFRASTRUCTURE GAPS IDENTIFIED:",
            f"  Lighting improvements needed:    {gaps.get('locations_needing_lighting', 0)} locations",
            f"  Call box coverage gaps:          {gaps.get('locations_needing_call_box', 0)} locations",
            f"  Isolated (low surveillance):     {gaps.get('isolated_locations', 0)} locations",
            "",
        ]

        if total_cost > 0:
            roi_pct = round((total_savings - total_cost) / total_cost * 100, 1) if total_cost > 0 else 0
            lines += [
                "INVESTMENT SUMMARY (ALL HOTSPOTS COMBINED):",
                f"  Total Infrastructure Cost:   ${total_cost:,}",
                f"  Incidents Prevented/Year:    {total_prevented}",
                f"  Projected Annual Savings:    ${total_savings:,}",
                f"  Overall ROI:                 {roi_pct}%",
                "",
            ]

        lines += ["TOP HOTSPOTS — ANALYSIS & RECOMMENDATIONS", "=" * 70, ""]

        for spot in spots:
            roi     = spot.get('roi', {})
            fin     = roi.get('financials', {})
            env     = spot.get('environmental_profile', {})

            lines += [
                f"#{spot['rank']} {spot['location_name']}",
                f"   Risk: {spot['risk_level']} ({spot['risk_score']:.1f}/10) | "
                f"Incidents: {spot['incident_count']} | CPTED Priority: {spot['cpted_priority']}",
                f"   Dominant Crime: {spot.get('dominant_crime', 'N/A')} | "
                f"VIIRS Lighting: {spot.get('viirs_luminance', 'N/A')} nW/cm²/sr "
                f"[{spot.get('viirs_label', 'N/A')}]",
            ]

            deficiencies = env.get('deficiencies', [])
            if deficiencies:
                lines.append("   Environmental Deficiencies:")
                for d in deficiencies[:4]:
                    lines.append(f"     ✗ {d}")

            lines.append("")
            lines.append("   CPTED Analysis:")
            lines.append(spot.get('cpted_report', 'N/A'))

            if roi.get('interventions'):
                lines += ["", "   Recommended Interventions:"]
                for iv in roi['interventions']:
                    lines += [
                        f"   PRIORITY {iv['priority']}: {iv['name']}",
                        f"     Cost:     ${iv['total_cost']:,} | "
                        f"Impact: {iv['reduction_pct_low']}-{iv['reduction_pct_high']}% reduction",
                        f"     Prevents: ~{iv['incidents_prevented']} incidents/year | "
                        f"Saves: ${iv['annual_savings']:,}/year",
                        f"     Evidence: {iv['citation_count']} peer-reviewed studies",
                    ]
                    for cite in iv['citations'][:1]:
                        lines.append(
                            f"       • {cite['authors']} ({cite['year']}): {cite['finding'][:80]}"
                        )
                lines += [
                    "",
                    f"   Total Investment: ${fin.get('total_infrastructure_cost', 0):,} | "
                    f"Annual Savings: ${fin.get('total_annual_savings', 0):,} | "
                    f"ROI: {fin.get('roi_percentage', 0)}% | "
                    f"Payback: {fin.get('payback_label', 'N/A')}",
                ]

            lines += ["", "-" * 70, ""]

        lines += [
            "METHODOLOGY",
            "=" * 70,
            "Crime Data: MU Campus Crime Log + Columbia PD 911 Dispatch",
            "Lighting:   VIIRS Satellite Nighttime Lights (EOG/NOAA)",
            "Roads:      US Census TIGER/Line 2025, Boone County MO",
            "Framework:  Crime Prevention Through Environmental Design (CPTED)",
            "RAG:        MU Annual Security Report, CPTED Guidelines, VAWA",
            "AI Models:  Multi-agent system (Safety Copilot + CPTED Agent)",
            "",
            "CONTACT",
            "MU Police Department: 573-882-7201",
            "Safe Ride: 573-882-1010 | Friend Walk: 573-884-9255",
            "=" * 70,
        ]

        with open(path, 'w') as f:
            f.write('\n'.join(lines))

        print(f"  Executive summary: {path}")
        return str(path)

    # ── Full export bundle ────────────────────────────────────────────────────

    def export_all(self, report: Dict) -> Dict:
        """Export all formats. Returns dict of file paths."""
        print("\n📤 Exporting reports...")
        ts = self._timestamp()
        return {
            'json':     self.export_json(report, f"campus_report_{ts}.json"),
            'csv_interventions': self.export_interventions_csv(
                report, f"interventions_{ts}.csv"
            ),
            'csv_risk':   self.export_risk_scores_csv(
                report, f"risk_scores_{ts}.csv"
            ),
            'summary':    self.export_executive_summary(
                report, f"executive_summary_{ts}.txt"
            ),
        }