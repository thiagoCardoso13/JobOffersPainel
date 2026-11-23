"""Generate the README screenshots from the local dashboard (needs Chrome installed).

Usage: streamlit run app.py --server.port 8501 &  &&  python scripts/screenshots.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
OUT = Path(__file__).resolve().parents[1] / "docs"


def esperar(page) -> None:
    page.wait_for_selector("text=Most requested skills", timeout=60000)
    page.wait_for_selector(".js-plotly-plot", timeout=60000)
    page.wait_for_timeout(3000)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    OUT.mkdir(exist_ok=True)
    # Streamlit scrolls inside a container, so the full-page shot uses a very tall viewport
    for nome, alto in [("dashboard-top", 900), ("dashboard-full", 2450)]:
        page = browser.new_page(viewport={"width": 1440, "height": alto}, color_scheme="light", device_scale_factor=1.5)
        page.goto(URL)
        esperar(page)
        page.screenshot(path=OUT / f"{nome}.png")
        page.close()
    browser.close()
print("ok")
