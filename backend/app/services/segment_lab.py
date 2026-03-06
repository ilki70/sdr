from __future__ import annotations

from app.services.vinac_lab import build_vinac_report, run_vinac_lab, summarize_vinac_results


SUPPORTED_SEGMENT_EVALUATIONS = {
    "consorcio_de_veiculos": "segment_consorcio_de_veiculos",
}


async def run_segment_lab(tenant_id: str, segment: str) -> tuple[list[dict], str]:
    if segment == "consorcio_de_veiculos":
        results = await run_vinac_lab(tenant_id)
        report = build_vinac_report(results).replace("VINAC Sales Lab Report", "Segment Sales Lab Report")
        return results, report
    raise ValueError(f"unsupported_segment:{segment}")


def summarize_segment_results(results: list[dict], segment: str) -> dict:
    summary = summarize_vinac_results(results)
    summary["segment"] = segment
    return summary
