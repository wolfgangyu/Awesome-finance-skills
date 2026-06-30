import json
import sys
from pathlib import Path

import requests
from loguru import logger


class DeepEarLiteTools:
    """
    Tools for fetching signals from DeepEar Lite.

    Supports two sources:
    - "remote": fetches from https://deepear.vercel.app/latest.json (default)
    - "local": reads from data/latest.json produced by alphaear-composer
    """

    LATEST_JSON_URL = "https://deepear.vercel.app/latest.json"
    # scripts/deepear_lite.py → parents[3] = repo root → data/latest.json
    _LOCAL_PATH = Path(__file__).resolve().parents[3] / "data" / "latest.json"

    def fetch_latest_signals(self, source: str = "remote") -> str:
        """
        Fetch signals from local or remote source.

        Args:
            source: "remote" (default, Vercel) or "local" (composer output)
        """
        if source == "local":
            return self._fetch_local()
        return self._fetch_remote()

    def _fetch_local(self) -> str:
        """Read from local latest.json (produced by alphaear-composer)."""
        path = self._LOCAL_PATH
        if not path.exists():
            return (
                f"No local latest.json found at {path}. "
                "Run alphaear-composer first, or use source='remote'."
            )

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return f"Error reading local latest.json: {e}"

        return self._format_signals(data)

    def _fetch_remote(self) -> str:
        """Fetch from DeepEar Vercel endpoint (original behavior)."""
        try:
            logger.info(f"Fetching data from {self.LATEST_JSON_URL}")
            headers = {
                "User-Agent": "DeepEar-Skill-Agent/1.0 (Awesome-Finance-Skills)",
                "Referer": "https://deepear.vercel.app/lite"
            }
            response = requests.get(self.LATEST_JSON_URL, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._format_signals(data)
        except Exception as e:
            error_msg = f"Error fetching DeepEar Lite data: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @staticmethod
    def _format_signals(data: dict) -> str:
        """Format signal data into a readable report string."""
        generated_at = data.get("generated_at", "Unknown")
        signals = data.get("signals", [])

        if not signals:
            return "No signals found in the latest data."

        report = [f"### DeepEar Lite Signal Report (Updated: {generated_at})\n"]

        for i, signal in enumerate(signals, 1):
            title = signal.get("title", "No Title")
            summary = signal.get("summary", "No Summary")
            sentiment = signal.get("sentiment_score", 0)
            confidence = signal.get("confidence", 0)
            intensity = signal.get("intensity", 0)
            reasoning = signal.get("reasoning", "No Reasoning")

            report.append(f"#### {i}. {title}")
            report.append(f"**Sentiment**: {sentiment} | **Confidence**: {confidence} | **Intensity**: {intensity}")
            report.append(f"\n**Summary**: {summary}")
            report.append(f"\n**Reasoning**: {reasoning}")

            # Check for sources/links
            sources = signal.get("sources", [])
            if sources:
                report.append("\n**Sources**:")
                for src in sources:
                    name = src.get("name", src.get("source_name", "Link"))
                    url = src.get("url", "#")
                    report.append(f"- [{name}]({url})")

            report.append("\n" + "-"*40 + "\n")

        return "\n".join(report)


if __name__ == "__main__":
    tools = DeepEarLiteTools()

    # Allow --local flag to switch to local source
    source = "local" if "--local" in sys.argv else "remote"
    print(tools.fetch_latest_signals(source=source))
