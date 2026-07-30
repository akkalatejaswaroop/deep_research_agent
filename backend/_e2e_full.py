"""Full end-to-end user query test with mocked network."""
import time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
import main as m
ti = time.perf_counter()
print(f"Import: {ti-t0:.1f}s")

# ------------------------------------------------------------------
# Mock network with realistic climate data
# ------------------------------------------------------------------
MOCK_SOURCES = {
    "nasa": {
        "url": "https://climate.nasa.gov/greenhouse-effect",
        "title": "NASA: The Greenhouse Effect",
        "domain": "climate.nasa.gov",
        "content": "The greenhouse effect is a natural process that warms Earth's surface. Greenhouse gases include carbon dioxide (CO2), methane (CH4), nitrous oxide (N2O), and fluorinated gases. These gases trap heat in the atmosphere. Without the natural greenhouse effect, Earth's average temperature would be about -18C instead of the current 15C. Human activities have increased CO2 levels from 280 ppm pre-industrial to over 420 ppm today."
    },
    "ipcc": {
        "url": "https://www.ipcc.ch/report/ar6/wg1",
        "title": "IPCC AR6 Climate Report",
        "domain": "ipcc.ch",
        "content": "The IPCC Sixth Assessment Report confirms that human activities have unequivocally caused global warming. Global surface temperature was 1.09C higher in 2011-2020 than 1850-1900. CO2 concentration has reached 420 ppm, the highest in at least 2 million years. Carbon dioxide is the most important long-lived greenhouse gas with a lifetime of hundreds to thousands of years. The equilibrium climate sensitivity is between 2.5 and 4C for a doubling of CO2."
    },
    "nature": {
        "url": "https://www.nature.com/articles/s41586-023-06783-9",
        "title": "Climate Feedback Loops",
        "domain": "nature.com",
        "content": "Climate feedback loops amplify global warming. The ice-albedo feedback occurs when melting ice reduces Earth's reflectivity causing more solar energy absorption. The permafrost feedback releases stored methane and CO2 as frozen ground thaws. The water vapor feedback increases atmospheric moisture as temperatures rise enhancing the greenhouse effect. The IPCC estimates equilibrium climate sensitivity between 2.5 and 4C for a doubling of CO2."
    },
    "noaa": {
        "url": "https://www.noaa.gov/climate",
        "title": "NOAA Climate.gov",
        "domain": "noaa.gov",
        "content": "Global warming refers to long-term heating of Earth's climate system due to human activities. Global average temperature has increased by approximately 1.2C since the late 19th century. 2024 was the warmest year on record. CO2 levels have risen from 280 ppm pre-industrial to over 420 ppm today. Sea level rise has accelerated from 1.4 mm per year in the 20th century to 3.6 mm per year since 2006."
    },
    "carbonbrief": {
        "url": "https://carbonbrief.org/co2-greenhouse-effect",
        "title": "Carbon Brief: CO2 and the Greenhouse Effect",
        "domain": "carbonbrief.org",
        "content": "Carbon dioxide is responsible for about two-thirds of the total warming effect from human-emitted greenhouse gases. The remaining third comes from methane, nitrous oxide, and F-gases. Methane is about 80 times more potent than CO2 over 20 years but has a shorter atmospheric lifetime of about 12 years. The warming effect follows: Delta F = 5.35 * ln(C/C0)."
    },
    "who": {
        "url": "https://www.who.int/news-room/fact-sheets/detail/climate-change-and-health",
        "title": "WHO: Climate Change and Health",
        "domain": "who.int",
        "content": "Climate change is the single biggest health threat facing humanity. Between 2030 and 2050 climate change is expected to cause approximately 250,000 additional deaths per year. Direct damage costs to health are estimated between 2-4 billion USD per year by 2030. Reducing emissions can improve health by reducing air pollution."
    },
    "sciencedaily": {
        "url": "https://www.sciencedaily.com/releases/2024/03/greenhouse-effect-study",
        "title": "ScienceDaily: New Breakthrough in Greenhouse Effect Research",
        "domain": "sciencedaily.com",
        "content": "A 2024 study published in Nature Geoscience found that the greenhouse effect has intensified by 50% since 1990 due to human emissions. The study used satellite measurements to track Earth's energy imbalance. Results show that CO2 remains the dominant driver, accounting for 65% of the increased forcing, followed by methane at 17%. The findings underscore the urgency of emissions reductions to meet Paris Agreement targets."
    },
    "energygov": {
        "url": "https://www.energy.gov/climate/greenhouse-gases-explained",
        "title": "US Department of Energy: Greenhouse Gases Explained",
        "domain": "energy.gov",
        "content": "The US Department of Energy reports that total US greenhouse gas emissions in 2023 were 5.8 billion metric tons of CO2 equivalent, a 1.1% decrease from 2022. Methane accounts for approximately 11% of US emissions. The energy sector is the largest source at 28% of total emissions. The DOE's research programs focus on carbon capture, renewable energy, and energy efficiency technologies to reduce emissions."
    },
    "unep": {
        "url": "https://www.unep.org/resources/emissions-gap-report-2024",
        "title": "UNEP Emissions Gap Report 2024",
        "domain": "unep.org",
        "content": "The UNEP Emissions Gap Report 2024 finds that Nations must collectively cut 42% off annual greenhouse gas emissions by 2030 and 57% by 2035 to limit global warming to 1.5C. Current policies put the world on track for a 2.6-3.1C temperature rise by 2100. Global greenhouse gas emissions reached a new high of 57.4 GtCO2e in 2023. The report warns that the gap between pledges and action remains dangerously large."
    },
    "mit": {
        "url": "https://climate.mit.edu/explainers/greenhouse-gases",
        "title": "MIT Climate Portal: Greenhouse Gases",
        "domain": "climate.mit.edu",
        "content": "MIT researchers explain that greenhouse gases vary widely in their global warming potential (GWP). Sulfur hexafluoride (SF6) has a GWP 23,500 times that of CO2 over 100 years. Methane's GWP is about 28 times CO2 over 100 years, but 80 times over 20 years. CO2 persists in the atmosphere for hundreds to thousands of years, while methane breaks down in about 12 years. Water vapor is the most abundant greenhouse gas but acts as a feedback, not a direct forcing."
    },
}

def _mock_search(query, **kwargs):
    return [dict(v, id=k+1) for k, (_, v) in enumerate(MOCK_SOURCES.items())]

m.search_all_sources = _mock_search
m.search_tavily = _mock_search
m.search_serpapi = _mock_search
m.search_wikipedia = _mock_search
m.search_web_duckduckgo = _mock_search

QUERY = "Explain the greenhouse effect and its impact on global warming"

stages = []
thoughts = []
urls_found = []

def on_node(node_id):
    stages.append(node_id)

def on_thought(msg):
    thoughts.append(msg)

def on_sources(urls):
    urls_found.extend(urls)

def on_track_status(tid, text, status):
    if status == "searching":
        on_thought(f"Track {tid}: Searching...")
    elif status == "synthesizing":
        on_thought(f"Track {tid}: Synthesizing...")
    elif status == "completed":
        on_thought(f"Track {tid}: Done")

print(f"\nUSER QUERY: {QUERY}\n")

t1 = time.perf_counter()
result = m.build_report_autonomously(
    query=QUERY,
    on_node=on_node,
    on_thought=on_thought,
    on_sources=on_sources,
    on_track_status=on_track_status,
)
tb = time.perf_counter()

print(f"{'='*72}")
print(f"STAGES: {' -> '.join(stages)}")
print(f"SOURCES: {len(urls_found)}")
print(f"THOUGHTS: {len(thoughts)}")
for t in thoughts[:10]:
    print(f"  \u2022 {t}")
if len(thoughts) > 10:
    print(f"  ... ({len(thoughts)-10} more)")

report = result.get("report", "")
prov = result.get("provenance", {})
metrics = result.get("_metrics", {})

print(f"\n{'='*72}")
print(f"REPORT ({len(report)} chars):")
print(f"{'='*72}")
sections = report.split("\n---\n")
for i, sec in enumerate(sections):
    heading = (sec.strip().split("\n")[0] or "(no heading)")[:90]
    body = sec.strip()[:600]
    print(f"\n--- [{i+1}] {heading} ---")
    print(body)
    if len(sec.strip()) > 600:
        print(f"  ... (+{len(sec.strip())-600} chars)")

print(f"\n{'='*72}")
print(f"PROVENANCE: {prov.get('total_claims',0)} claims total")
cov = prov.get("coverage", {})
print(f"  Multi-sourced: {cov.get('multi_sourced',0)} | Single-source: {cov.get('single_source',0)} | Uncited: {cov.get('uncited',0)}")
print(f"  Top sources:")
for s in prov.get("source_utilisation", [])[:4]:
    if s.get("claim_count", 0) > 0:
        print(f"    [{s.get('id')}] {s.get('domain')}: {s.get('claim_count')} claims")

print(f"\n{'='*72}")
print(f"METRICS: Overall {metrics.get('quality',{}).get('overall','?')}/10")
scores = metrics.get("quality", {}).get("scores", {})
print(f"  " + " | ".join(f"{k}: {scores.get(k,'?')}" for k in ["relevance","depth","novelty","coherence","citation_accuracy"]))

print(f"\n{'='*72}")
print(f"Timing: import={ti-t0:.1f}s  build={tb-t1:.1f}s  total={tb-t0:.1f}s")
print(f"Sub-questions: {len(result.get('synthesis_results',[]))}")
print(f"Provenance: {'YES' if prov else 'no'}")
print(f"{'='*72}")
print("RESULT: PASS")
